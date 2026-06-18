"""
WorldMonitor scraper — fetches briefs from the local WorldMonitor API.

WorldMonitor provides curated global event/trend briefs. We extract those
that describe emerging problems, crises, or disruptions. Tier 1 source.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import TYPE_CHECKING

import httpx

from scout.scrapers.base import safe_fetch

if TYPE_CHECKING:
    from scout.config import Settings

logger = logging.getLogger(__name__)

# Problem-indicator keywords for heuristic filtering.
PROBLEM_KEYWORDS: list[str] = [
    "crisis",
    "shortage",
    "disruption",
    "gap",
    "failure",
    "outage",
    "breakdown",
    "collapse",
    "deficit",
    "emergency",
    "bottleneck",
    "vulnerability",
    "breakdown",
    "deficiency",
    "degradation",
    "crippling",
    "debilitating",
    "catastrophic",
    "catastrophe",
    "shutdown",
    "blackout",
    "meltdown",
    "scandal",
    "breach",
    "hack",
    "cyberattack",
    "recall",
    "contamination",
    "spill",
    "shortfall",
    "drought",
    "famine",
    "pandemic",
    "epidemic",
    "outbreak",
    "surge",
    "spike",
    "plunge",
    "crash",
    "freeze",
    "lockdown",
    "sanction",
    "embargo",
    "tariff",
    "boycott",
    "strike",
    "walkout",
    "protest",
    "riot",
    "unrest",
    "instability",
    "turmoil",
]


def _contains_problem_signal(text: str) -> bool:
    """Check if text contains any problem-indicator keywords (case-insensitive)."""
    lower = text.lower()
    return any(kw in lower for kw in PROBLEM_KEYWORDS)


def _truncate(text: str, max_len: int = 80) -> str:
    stripped = text.strip().replace("\n", " ")
    if len(stripped) <= max_len:
        return stripped
    return stripped[: max_len - 1].rstrip() + "…"


async def fetch_worldmonitor(settings: Settings, backfill: bool = False) -> list[dict]:
    """Fetch WorldMonitor briefs and extract problem signals.

    Calls the local WorldMonitor API's /api/briefs endpoint. Each brief is
    checked against a heuristic keyword list for problem indicators.

    Returns list[dict] with keys title, text, url, source_type, source_tier,
    discovered_at. Gracefully returns [] if WorldMonitor is unreachable.
    """
    limit = 50 if backfill else 20
    url = f"{settings.worldmonitor_url}/api/briefs?limit={limit}"
    timeout = httpx.Timeout(10.0, connect=5.0)

    async with httpx.AsyncClient(timeout=timeout) as client:
        try:
            resp = await client.get(url)
            resp.raise_for_status()
            data = resp.json()
        except httpx.ConnectError:
            logger.warning("WorldMonitor unreachable at %s", settings.worldmonitor_url)
            return []
        except httpx.TimeoutException:
            logger.warning("WorldMonitor timed out at %s", settings.worldmonitor_url)
            return []
        except Exception:
            logger.exception("WorldMonitor fetch failed")
            return []

    briefs = data if isinstance(data, list) else data.get("briefs", data.get("data", []))
    results: list[dict] = []

    for brief in briefs:
        if not isinstance(brief, dict):
            continue

        title = brief.get("title", "") or brief.get("headline", "")
        summary = brief.get("summary", "") or brief.get("description", "") or brief.get("body", "")
        brief_url = brief.get("url", "") or brief.get("link", "") or settings.worldmonitor_url

        combined = f"{title} {summary}"
        if not _contains_problem_signal(combined):
            continue

        results.append({
            "title": _truncate(title or summary),
            "text": summary or title,
            "url": brief_url,
            "source_type": "worldmonitor",
            "source_tier": 1,
            "discovered_at": datetime.now(timezone.utc).isoformat(),
        })

    logger.info("WorldMonitor: %d problem-signal briefs found", len(results))
    return results
