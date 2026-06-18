"""
Scraping → extraction → dedup → scoring → storage pipeline.
Runs on a configurable interval during active hours.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import re
from datetime import datetime, timezone

from openai import AsyncOpenAI

from scout.config import Settings, load_profile
from scout.db import Database
from scout.kg import KnowledgeGraph
from scout.scoring import Idea, ScoreReport, extract_problems, score_idea

logger = logging.getLogger(__name__)

_WORD = re.compile(r"\w+")


def _tokenize(text: str) -> set[str]:
    return set(_WORD.findall(text.lower()))


class Pipeline:

    def __init__(self, settings: Settings):
        self.settings = settings
        self.db = Database(settings.db_path)
        self.profile = load_profile(settings.profile_path)
        self.kg = KnowledgeGraph(settings.graph_path)
        self.llm = (
            AsyncOpenAI(api_key=settings.openai_api_key)
            if settings.openai_api_key
            else None
        )
        self.running = False
        self._cycle_count = 0

    @staticmethod
    def _make_idea_id(title: str, source_url: str) -> str:
        tag = hashlib.sha256(f"{title}|{source_url}".encode()).hexdigest()[:12]
        return f"idea-{tag}"

    @staticmethod
    def _jaccard(a: set[str], b: set[str]) -> float:
        if not a or not b:
            return 0.0
        return len(a & b) / len(a | b)

    @staticmethod
    def _is_active_hour(settings: Settings) -> bool:
        now = datetime.now(timezone.utc)
        return settings.active_hours_start <= now.hour < settings.active_hours_end

    async def run_once(self) -> dict:
        from scout.scrapers import (
            fetch_github_issues,
            fetch_hn,
            fetch_jobs,
            fetch_news,
            fetch_reddit,
            fetch_reviews,
            fetch_twitter,
            fetch_worldmonitor,
        )

        self._cycle_count += 1

        # 1. Scrape concurrently (frequency-gated)
        tasks: list = [
            fetch_reddit(self.settings),
            fetch_hn(self.settings),
            fetch_news(self.settings),
            fetch_twitter(self.settings),
            fetch_worldmonitor(self.settings),
            fetch_github_issues(self.settings),
        ]
        if self._cycle_count % 2 == 0:
            tasks.append(fetch_reviews(self.settings))
        if self._cycle_count % 4 == 0:
            tasks.append(fetch_jobs(self.settings))

        results = await asyncio.gather(*tasks, return_exceptions=True)

        all_signals: list[dict] = []
        for r in results:
            if isinstance(r, Exception):
                logger.warning("Scraper error: %s", r)
            elif isinstance(r, list):
                all_signals.extend(r)

        signals_found = len(all_signals)

        # 2. Store raw signals
        for sig in all_signals:
            self.db.store_raw_signal(sig)

        # 3. Extract problems from unprocessed signals
        unprocessed = self.db.get_unprocessed_signals(limit=200)
        problems: list[dict] = []

        for sig in unprocessed:
            text = sig.get("text") or sig.get("title") or ""

            if self.llm:
                try:
                    extracted = await extract_problems(
                        text,
                        sig.get("source_type", "unknown"),
                        self.llm,
                    )
                except Exception:
                    logger.warning(
                        "extract_problems failed for signal %s", sig.get("id"),
                        exc_info=True,
                    )
                    extracted = []
            else:
                extracted = []

            for p in extracted:
                p["source_url"] = sig["url"]
                p["source_type"] = sig["source_type"]
                p["source_tier"] = sig["source_tier"]
                p["discovered_at"] = sig["discovered_at"]
            problems.extend(extracted)

            if not extracted:
                problems.append({
                    "title": sig.get("title", "Untitled signal"),
                    "description": (text or sig.get("title", ""))[:500],
                    "severity": 3,
                    "source_url": sig["url"],
                    "source_type": sig["source_type"],
                    "source_tier": sig["source_tier"],
                    "discovered_at": sig["discovered_at"],
                })

            self.db.mark_signal_processed(sig["id"])

        problems_extracted = len(problems)

        # 4. Semantic dedup (Jaccard title overlap > 0.7)
        unique: list[dict] = []
        tokens_list: list[set[str]] = []

        for p in problems:
            tok = _tokenize(p["title"])
            dup_idx: int | None = None
            for i, existing_tok in enumerate(tokens_list):
                if self._jaccard(tok, existing_tok) > 0.7:
                    dup_idx = i
                    break

            if dup_idx is not None:
                existing_tier = unique[dup_idx].get("source_tier", 5)
                new_tier = p.get("source_tier", 5)
                if new_tier < existing_tier:
                    unique[dup_idx] = p
            else:
                tokens_list.append(tok)
                unique.append(p)

        # 5. Score each unique idea
        ideas_scored = 0
        verdicts = {"STRONG": 0, "PROMISING": 0, "WEAK": 0, "TARPIT": 0, "REJECT": 0}

        for p in unique:
            idea = Idea(
                id=self._make_idea_id(p["title"], p["source_url"]),
                title=p["title"],
                description=p.get("description", ""),
                source_url=p["source_url"],
                source_type=p["source_type"],
                source_tier=int(p.get("source_tier", 5)),
                discovered_at=_parse_dt(p.get("discovered_at")),
                embedding=None,
            )

            self.db.store_idea(idea)

            if self.llm is not None:
                try:
                    report = await score_idea(idea, self.profile, self.kg, self.llm)
                except Exception:
                    logger.warning("Scoring failed for %s", idea.id, exc_info=True)
                    report = _fallback_report(idea.id, "Scoring failed")
            else:
                report = _fallback_report(idea.id, "No LLM configured")

            self.db.store_score(report)
            ideas_scored += 1
            verdicts[report.verdict] = verdicts.get(report.verdict, 0) + 1

        # 6. Push mentions to active deep-dives
        for dive in self.db.get_active_deep_dives():
            for p in problems:
                if p.get("source_url"):
                    self.db.link_mention(dive["idea_id"], p["source_url"])

        return {
            "signals_found": signals_found,
            "problems_extracted": problems_extracted,
            "ideas_scored": ideas_scored,
            "strong": verdicts["STRONG"],
            "promising": verdicts["PROMISING"],
            "weak": verdicts["WEAK"],
            "rejected": verdicts["REJECT"],
        }

    async def run_loop(self) -> None:
        self.running = True
        logger.info("Pipeline loop started (interval=%dm)", self.settings.scrape_interval_minutes)
        while self.running:
            if not self._is_active_hour(self.settings):
                await asyncio.sleep(300)
                continue

            try:
                stats = await self.run_once()
                logger.info("Cycle %d: %s", self._cycle_count, json.dumps(stats))
            except Exception:
                logger.error("Pipeline cycle %d crashed", self._cycle_count, exc_info=True)

            await asyncio.sleep(self.settings.scrape_interval_minutes * 60)

    async def process_deep_dives(self) -> None:
        logger.info("Deep-dive processor started (interval=%dm)", self.settings.deep_dive_interval_minutes)
        while self.running:
            if not self.llm:
                await asyncio.sleep(self.settings.deep_dive_interval_minutes * 60)
                continue
            try:
                for dive in self.db.get_active_deep_dives():
                    logger.debug("Deep-dive tick for idea %s", dive["idea_id"])
            except Exception:
                logger.error("Deep-dive processor error", exc_info=True)
            await asyncio.sleep(self.settings.deep_dive_interval_minutes * 60)

    async def stop(self) -> None:
        self.running = False
        logger.info("Pipeline stop signalled")


async def create_pipeline() -> Pipeline:
    return Pipeline(Settings())


def _parse_dt(val) -> datetime:
    if isinstance(val, datetime):
        return val
    if isinstance(val, str):
        val = val.replace("Z", "+00:00")
        return datetime.fromisoformat(val)
    return datetime.now(timezone.utc)


def _fallback_report(idea_id: str, reason: str) -> ScoreReport:
    return ScoreReport(
        idea_id=idea_id,
        composite=0.0,
        problem_quality=0.0,
        market_viability=0.0,
        sentiment_signal=0.0,
        founder_fit=0.0,
        sentiment_flags=[],
        risks=[reason],
        tarpit=None,
        failure_matches=[],
        verdict="WEAK",
        justification=reason,
    )
