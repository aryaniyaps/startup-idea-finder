"""
SQLite storage layer via sqlite-utils.
Manages raw signals, scored ideas, mentions, dedup groups, and deep-dives.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import sqlite_utils


class Database:
    """Persistent storage for the Idea Scout pipeline and dashboard."""

    def __init__(self, db_path: str):
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite_utils.Database(db_path)
        self.db.conn.execute("PRAGMA journal_mode=WAL")
        self.db.conn.execute("PRAGMA foreign_keys=ON")
        self._init_schema()

    # ------------------------------------------------------------------
    # Schema
    # ------------------------------------------------------------------

    def _init_schema(self) -> None:
        existing = set(self.db.table_names())

        if "raw_signals" not in existing:
            self.db["raw_signals"].create(
                {
                    "id": int,
                    "title": str,
                    "text": str,
                    "url": str,
                    "source_type": str,
                    "source_tier": int,
                    "discovered_at": str,
                    "created_at": str,
                    "processed": bool,
                },
                pk="id",
            )

        if "ideas" not in existing:
            self.db["ideas"].create(
                {
                    "id": str,
                    "title": str,
                    "description": str,
                    "source_url": str,
                    "source_type": str,
                    "source_tier": int,
                    "discovered_at": str,
                    "created_at": str,
                    "embedding": str,  # JSON-serialised list[float] or NULL
                },
                pk="id",
            )

        if "scores" not in existing:
            self.db["scores"].create(
                {
                    "id": int,
                    "idea_id": str,
                    "composite": float,
                    "problem_quality": float,
                    "market_viability": float,
                    "sentiment_signal": float,
                    "founder_fit": float,
                    "sentiment_flags": str,  # JSON list[str]
                    "risks": str,  # JSON list[str]
                    "tarpit": str,  # JSON dict or NULL
                    "failure_matches": str,  # JSON list[str]
                    "verdict": str,
                    "justification": str,
                    "scored_at": str,
                },
                pk="id",
                foreign_keys=[("idea_id", "ideas", "id")],
            )

        if "mentions" not in existing:
            self.db["mentions"].create(
                {
                    "id": int,
                    "idea_id": str,
                    "source_url": str,
                    "source_type": str,
                    "discovered_at": str,
                },
                pk="id",
                foreign_keys=[("idea_id", "ideas", "id")],
            )

        if "dedup_groups" not in existing:
            self.db["dedup_groups"].create(
                {
                    "id": int,
                    "idea_ids": str,  # JSON list[str]
                    "created_at": str,
                },
                pk="id",
            )

        if "deep_dives" not in existing:
            self.db["deep_dives"].create(
                {
                    "id": int,
                    "idea_id": str,
                    "status": str,
                    "research_notes": str,  # JSON dict
                    "created_at": str,
                    "updated_at": str,
                },
                pk="id",
                foreign_keys=[("idea_id", "ideas", "id")],
            )

        if "derived_problems" not in existing:
            self.db["derived_problems"].create(
                {
                    "id": str,
                    "title": str,
                    "description": str,
                    "category": str,
                    "affected_demographic": str,
                    "signal_count": int,
                    "source_tiers": str,  # JSON list[int]
                    "severity": float,
                    "problem_quality": float,
                    "market_viability": float,
                    "composite_score": float,
                    "framework_scores": str,  # JSON dict
                    "risks": str,  # JSON list[str]
                    "tarpit_check": str,  # JSON dict or NULL
                    "failure_matches": str,  # JSON list[str]
                    "innovative_solutions": str,  # JSON list[dict]
                    "created_at": str,
                },
                pk="id",
            )

        # Indexes (idempotent via if_not_exists)
        self.db["ideas"].create_index(["source_tier"], if_not_exists=True)
        self.db["scores"].create_index(["composite"], if_not_exists=True)
        self.db["scores"].create_index(["verdict"], if_not_exists=True)
        self.db["mentions"].create_index(["idea_id"], if_not_exists=True)
        self.db["raw_signals"].create_index(["processed"], if_not_exists=True)

    # ------------------------------------------------------------------
    # Raw signals
    # ------------------------------------------------------------------


    def get_signals(
        self,
        limit: int = 50,
        offset: int = 0,
        source_type: str | None = None,
        min_tier: int | None = None,
    ) -> list[dict]:
        """Return raw signals paginated, newest first. Includes idea/score data when processed."""
        sql = """
        SELECT rs.*, i.id AS idea_id, i.title AS idea_title,
               s.composite, s.verdict
        FROM raw_signals rs
        LEFT JOIN mentions m ON rs.url = m.source_url
        LEFT JOIN ideas i ON m.idea_id = i.id
        LEFT JOIN (
            SELECT idea_id, MAX(id) AS max_id FROM scores GROUP BY idea_id
        ) latest ON i.id = latest.idea_id
        LEFT JOIN scores s ON s.id = latest.max_id
        WHERE 1=1
        """
        params: dict = {}
        if source_type:
            sql += " AND rs.source_type = :st"
            params["st"] = source_type
        if min_tier is not None:
            sql += " AND rs.source_tier >= :mt"
            params["mt"] = min_tier
        sql += " ORDER BY rs.discovered_at DESC LIMIT :limit OFFSET :offset"
        params["limit"] = limit
        params["offset"] = offset

        rows = list(self.db.query(sql, params))
        return [dict(r) for r in rows]

    def store_raw_signal(self, signal: dict) -> int:
        """Persist a raw signal dict; returns its auto-incremented id."""
        signal = dict(signal)
        signal.setdefault("created_at", _now())
        signal.setdefault("processed", False)
        signal = _coerce_row(signal)
        return self.db["raw_signals"].insert(signal).last_pk

    def get_unprocessed_signals(self, limit: int = 100) -> list[dict]:
        rows = self.db["raw_signals"].rows_where(
            "processed = 0", limit=limit, order_by="id"
        )
        return [dict(r) for r in rows]

    def mark_signal_processed(self, signal_id: int) -> None:
        self.db["raw_signals"].update(signal_id, {"processed": True})

    def get_signal_stats(self) -> dict:
        """Aggregate stats for raw signals."""
        total_signals = self.db["raw_signals"].count
        processed_count = self.db["raw_signals"].count_where("processed = 1")

        by_source: dict[str, int] = {}
        for row in self.db.query(
            "SELECT source_type, COUNT(*) AS cnt FROM raw_signals GROUP BY source_type"
        ):
            by_source[row["source_type"]] = row["cnt"]

        by_tier: dict[str, int] = {}
        for row in self.db.query(
            "SELECT source_tier, COUNT(*) AS cnt FROM raw_signals GROUP BY source_tier"
        ):
            by_tier[f"tier_{row['source_tier']}"] = row["cnt"]

        by_date: dict[str, int] = {}
        for row in self.db.query(
            """
            SELECT DATE(discovered_at) AS day, COUNT(*) AS cnt
            FROM raw_signals
            WHERE discovered_at >= DATE('now', '-30 days')
            GROUP BY day
            ORDER BY day
            """
        ):
            by_date[row["day"]] = row["cnt"]

        return {
            "total_signals": total_signals,
            "processed_count": processed_count,
            "unprocessed_count": total_signals - processed_count,
            "by_source": by_source,
            "by_tier": by_tier,
            "by_date": by_date,
        }

    # ------------------------------------------------------------------
    # Ideas
    # ------------------------------------------------------------------

    def store_idea(self, idea) -> None:
        """Insert or replace an Idea dataclass instance."""
        d = _dataclass_to_row(idea)
        d["discovered_at"] = _iso(d["discovered_at"])
        d.setdefault("created_at", _now())
        if d.get("embedding") is not None:
            d["embedding"] = json.dumps(d["embedding"])
        else:
            d["embedding"] = None
        self.db["ideas"].upsert(d, pk="id")

    # ------------------------------------------------------------------
    # Scores
    # ------------------------------------------------------------------

    def store_score(self, report) -> None:
        """Persist a ScoreReport dataclass instance."""
        d = _dataclass_to_row(report)
        d["scored_at"] = _now()
        for json_field in ("sentiment_flags", "risks", "failure_matches"):
            d[json_field] = json.dumps(d.get(json_field, []) or [])
        d["tarpit"] = json.dumps(d["tarpit"]) if d.get("tarpit") else None
        self.db["scores"].insert(d)

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    def get_ideas(
        self, limit: int = 50, offset: int = 0, min_score: float = 0, verdict: str | None = None
    ) -> list[dict]:
        """Return ideas joined with their latest score, ordered by composite desc."""
        sql = """
        SELECT i.*, s.composite, s.verdict, s.sentiment_flags, s.risks, s.justification,
               s.problem_quality, s.market_viability, s.sentiment_signal, s.founder_fit
        FROM ideas i
        LEFT JOIN (
            SELECT idea_id, MAX(id) AS max_id FROM scores GROUP BY idea_id
        ) latest ON i.id = latest.idea_id
        LEFT JOIN scores s ON s.id = latest.max_id
        WHERE 1=1
        """
        params: dict = {}
        if min_score > 0:
            sql += " AND COALESCE(s.composite, 0) >= :min_score"
            params["min_score"] = min_score
        if verdict:
            sql += " AND s.verdict = :verdict"
            params["verdict"] = verdict
        sql += " ORDER BY COALESCE(s.composite, 0) DESC LIMIT :limit OFFSET :offset"
        params["limit"] = limit
        params["offset"] = offset

        rows = list(self.db.query(sql, params))
        for row in rows:
            _hydrate_json(row, "embedding")
            _hydrate_json(row, "sentiment_flags")
            _hydrate_json(row, "risks")
        return rows

    def get_idea_detail(self, idea_id: str) -> dict | None:
        idea_rows = list(self.db["ideas"].rows_where("id = ?", [idea_id]))
        if not idea_rows:
            return None
        idea = dict(idea_rows[0])
        _hydrate_json(idea, "embedding")

        # Latest score
        score_rows = list(
            self.db["scores"].rows_where(
                "idea_id = ?", [idea_id], order_by="id desc", limit=1
            )
        )
        if score_rows:
            score = dict(score_rows[0])
            for field in ("sentiment_flags", "risks", "failure_matches", "tarpit"):
                _hydrate_json(score, field)
            idea["score"] = score

        # Related mentions
        mentions = list(self.db["mentions"].rows_where("idea_id = ?", [idea_id]))
        idea["mentions"] = [dict(m) for m in mentions]

        return idea

    def get_stats(self) -> dict:
        """Aggregate statistics for the dashboard."""
        total_ideas = self.db["ideas"].count
        total_signals = self.db["raw_signals"].count

        by_verdict: dict[str, int] = {}
        for row in self.db.query(
            """
            SELECT s.verdict, COUNT(*) AS cnt
            FROM scores s
            INNER JOIN (
                SELECT idea_id, MAX(id) AS max_id FROM scores GROUP BY idea_id
            ) latest ON s.id = latest.max_id
            GROUP BY s.verdict
            """
        ):
            by_verdict[row["verdict"] or "UNKNOWN"] = row["cnt"]

        by_source: dict[str, int] = {}
        for row in self.db.query(
            "SELECT source_type, COUNT(*) AS cnt FROM ideas GROUP BY source_type"
        ):
            by_source[row["source_type"]] = row["cnt"]

        by_tier: dict[str, int] = {}
        for row in self.db.query(
            "SELECT source_tier, COUNT(*) AS cnt FROM ideas GROUP BY source_tier"
        ):
            by_tier[f"tier_{row['source_tier']}"] = row["cnt"]

        top_ideas = self.get_ideas(limit=5, min_score=0)

        return {
            "total_ideas": total_ideas,
            "total_signals": total_signals,
            "by_verdict": by_verdict,
            "by_source": by_source,
            "by_tier": by_tier,
            "top_ideas": top_ideas,
        }

    # ------------------------------------------------------------------
    # Dedup & mentions
    # ------------------------------------------------------------------

    def mark_dedup_group(self, idea_ids: list[str]) -> None:
        self.db["dedup_groups"].insert(
            {"idea_ids": json.dumps(idea_ids), "created_at": _now()}
        )

    def link_mention(self, idea_id: str, source_url: str) -> None:
        # Resolve source_type from the raw signal that has this URL
        signals = list(
            self.db["raw_signals"].rows_where("url = ?", [source_url], limit=1)
        )
        source_type = signals[0]["source_type"] if signals else "unknown"
        discovered_at = signals[0]["discovered_at"] if signals else _now()

        # Avoid duplicates
        existing = list(
            self.db["mentions"].rows_where(
                "idea_id = ? AND source_url = ?", [idea_id, source_url], limit=1
            )
        )
        if existing:
            return

        self.db["mentions"].insert(
            {
                "idea_id": idea_id,
                "source_url": source_url,
                "source_type": source_type,
                "discovered_at": discovered_at,
            }
        )

    # ------------------------------------------------------------------
    # Deep dives
    # ------------------------------------------------------------------

    def create_deep_dive(self, idea_id: str) -> int:
        now = _now()
        return (
            self.db["deep_dives"]
            .insert(
                {
                    "idea_id": idea_id,
                    "status": "active",
                    "research_notes": json.dumps({}),
                    "created_at": now,
                    "updated_at": now,
                }
            )
            .last_pk
        )

    def update_deep_dive(self, idea_id: str, status: str, notes: dict) -> None:
        dive_rows = list(
            self.db["deep_dives"].rows_where(
                "idea_id = ?", [idea_id], order_by="id desc", limit=1
            )
        )
        if not dive_rows:
            self.create_deep_dive(idea_id)
            dive_rows = list(
                self.db["deep_dives"].rows_where(
                    "idea_id = ?", [idea_id], order_by="id desc", limit=1
                )
            )
        self.db["deep_dives"].update(
            dive_rows[0]["id"],
            {
                "status": status,
                "research_notes": json.dumps(notes),
                "updated_at": _now(),
            },
        )

    def get_active_deep_dives(self) -> list[dict]:
        rows = list(self.db["deep_dives"].rows_where("status = 'active'"))
        result: list[dict] = []
        for r in rows:
            d = dict(r)
            _hydrate_json(d, "research_notes")
            result.append(d)
        return result

    # ------------------------------------------------------------------
    # Derived problems
    # ------------------------------------------------------------------

    def store_derived_problem(self, problem) -> None:
        """Insert or upsert a DerivedProblem dataclass or dict."""
        if hasattr(problem, "to_row"):
            d = problem.to_row()
        else:
            d = dict(problem)
        d.setdefault("created_at", _now())
        d = _coerce_row(d)
        self.db["derived_problems"].upsert(d, pk="id")

    def get_derived_problems(self, limit: int = 20, offset: int = 0) -> list[dict]:
        """Return paginated derived problems ordered by composite_score desc."""
        rows = list(
            self.db["derived_problems"].rows_where(
                "1=1", limit=limit, offset=offset, order_by="composite_score desc"
            )
        )
        result: list[dict] = []
        for r in rows:
            d = dict(r)
            for json_field in (
                "source_tiers",
                "framework_scores",
                "risks",
                "tarpit_check",
                "failure_matches",
                "innovative_solutions",
            ):
                _hydrate_json(d, json_field)
            result.append(d)
        return result


# ------------------------------------------------------------------
# Internal helpers
# ------------------------------------------------------------------

def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _iso(val) -> str:
    """Convert a datetime to ISO string, pass through strings."""
    if isinstance(val, datetime):
        return val.isoformat()
    return str(val)


def _coerce_row(d: dict) -> dict:
    """Ensure dict values are JSON-safe types sqlite-utils can insert."""
    out = {}
    for k, v in d.items():
        if isinstance(v, (int, float, str, bool, type(None))):
            out[k] = v
        elif isinstance(v, datetime):
            out[k] = v.isoformat()
        elif isinstance(v, (list, dict)):
            out[k] = json.dumps(v)
        else:
            out[k] = str(v)
    return out


def _dataclass_to_row(obj) -> dict:
    """Convert a dataclass instance to a plain dict for storage."""
    import dataclasses

    return dataclasses.asdict(obj)


def _hydrate_json(row: dict, key: str) -> None:
    """Parse a JSON string column in-place if present and non-None."""
    val = row.get(key)
    if isinstance(val, str):
        try:
            row[key] = json.loads(val)
        except (json.JSONDecodeError, TypeError):
            pass
