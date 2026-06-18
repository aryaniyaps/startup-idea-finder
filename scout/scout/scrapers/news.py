"""
RSS feed scraper for news sources.

Parses technology and business RSS feeds, filtering for articles
that mention problems, gaps, or challenges relevant to the user's industries.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import TYPE_CHECKING

import feedparser
import httpx

from .base import safe_fetch

if TYPE_CHECKING:
    from scout.config import Settings

logger = logging.getLogger(__name__)

FEEDS = [
    ("https://hnrss.org/frontpage", "hnrss"),
    ("https://techcrunch.com/feed/", "techcrunch"),
    ("https://feeds.arstechnica.com/arstechnica/index", "ars_technica"),
    ("https://www.theverge.com/rss/index.xml", "the_verge"),
]

MAX_RESULTS = 20

# Heuristic phrases that indicate a problem or market gap in article text.
PROBLEM_PHRASES = [
    "struggling with",
    "facing",
    "challenge",
    "gap in",
    "shortage of",
    "lack of",
    "need for",
    "can't keep up",
    "not enough",
    "outpaced",
    "failing to",
    "unmet demand",
    "underserved",
    "crisis",
    "bottleneck",
    "broken",
]


def _matches_problem(text: str) -> bool:
    """Check whether text contains problem-indicating phrases."""
    lower = text.lower()
    return any(phrase in lower for phrase in PROBLEM_PHRASES)


def _matches_industry(text: str, industries: list[str]) -> bool:
    """Check whether text references any of the user's industries."""
    if not industries:
        return True  # No filter → pass everything.
    lower = text.lower()
    return any(ind.lower() in lower for ind in industries)


async def _process_feed(
    client: httpx.AsyncClient,
    url: str,
    source_label: str,
    industries: list[str],
    discovered_at: str,
) -> list[dict]:
    """Fetch and process a single RSS feed."""
    xml = await safe_fetch(client, url)
    if not xml:
        logger.warning("news: empty response from %s", url)
        return []

    feed = feedparser.parse(xml)
    if feed.bozo and not feed.entries:
        logger.warning("news: feed %s parse error: %s", url, feed.bozo_exception)
        return []

    signals: list[dict] = []
    for entry in feed.entries:
        title = (entry.get("title") or "").strip()
        summary = (entry.get("summary") or "").strip()
        combined = f"{title}\n{summary}"

        if not _matches_problem(combined):
            continue
        if not _matches_industry(combined, industries):
            continue

        entry_url = entry.get("link") or url
        text = summary
        # Prefer full content if available via content or description.
        content_list = entry.get("content")
        if content_list and len(content_list) > 0:
            full = content_list[0].get("value", "")
            if full:
                text = full
        elif entry.get("description"):
            text = entry.get("description", "")

        signals.append({
            "title": title,
            "text": text,
            "url": entry_url,
            "source_type": "news",
            "source_tier": 1,
            "discovered_at": discovered_at,
        })

        if len(signals) >= MAX_RESULTS:
            break

    logger.debug("news: %d signals from %s", len(signals), url)
    return signals


async def fetch_news(settings: "Settings") -> list[dict]:
    """
    Fetch recent news articles and extract problem-signaling content.

    Returns list[dict] with keys:
      title, text, url, source_type, source_tier, discovered_at

    Filters against user profile industries and problem heuristics.
    Limited to MAX_RESULTS across all feeds.
    """
    discovered_at = datetime.now(timezone.utc).isoformat()

    # Extract user industries from settings (lazy import to avoid
    # circular dependency; the profile is loaded from config).
    try:
        from scout.config import load_profile

        profile = load_profile(settings.profile_path)
        industries = profile.industries
    except Exception:
        industries = []

    async with httpx.AsyncClient(timeout=30) as client:
        tasks = [
            _process_feed(client, url, label, industries, discovered_at)
            for url, label in FEEDS
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)

    all_signals: list[dict] = []
    for r in results:
        if isinstance(r, list):
            all_signals.extend(r)
        else:
            logger.warning("news: feed processing failed: %s", r)

    # Sort by recency (most entries have published_parsed) and limit.
    all_signals = all_signals[:MAX_RESULTS]
    logger.info("news: %d total signals", len(all_signals))
    return all_signals
