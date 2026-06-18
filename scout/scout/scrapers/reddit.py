"""
Reddit scraper — CamoFox stealth browser via REST API.
Uses camofox-browser macros for subreddit navigation and search.
Zero API keys. C++ engine-level anti-detection.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from scout.scrapers.browser_client import BrowserClient, _extract_texts, _extract_links

if TYPE_CHECKING:
    from scout.config import Settings

logger = logging.getLogger(__name__)

# ── Seed subreddits to monitor ──────────────────────────────────────────
SEED_SUBREDDITS: list[str] = [
    "startups",
    "Entrepreneur",
    "smallbusiness",
    "SaaS",
    "webdev",
    "programming",
    "sysadmin",
    "freelance",
]

# ── Industry subreddits ─────────────────────────────────────────────────
INDUSTRY_SUBREDDITS: list[str] = [
    "legaltech",
    "healthIT",
    "accounting",
    "logistics",
    "Insurance",
    "edtech",
    "realestate",
    "manufacturing",
]

# ── Search queries for Reddit search macro ──────────────────────────────
SEARCH_QUERIES: list[str] = [
    "manual process workaround",
    "hate this software alternative",
    "looking for a tool",
    "someone should build",
    "wish there was an app",
    "frustrated with",
    "any recommendations for software",
]

# ── Problem-indicator keywords for filtering ────────────────────────────
PROBLEM_KEYWORDS: list[str] = [
    "hate", "frustrated", "nightmare", "killing me", "can't stand", "ruining",
    "infuriating", "garbage", "useless", "terrible", "driving me crazy",
    "manual", "spreadsheet", "workaround", "duct tape", "hacky", "janky",
    "copy-paste", "copy paste", "excel", "manually",
    "any tool for", "does anyone else", "why is there no",
    "someone should build", "wish there was", "looking for a",
    "alternative to", "is there a way to", "anyone know of", "need something that",
    "desperate", "please someone", "i would pay anything",
    "this is costing us", "paying for", "costs us", "spent $",
]

# ── Constants ────────────────────────────────────────────────────────────
REQUEST_DELAY = 2.0  # seconds between subreddit/query requests


def _matches_problem(text: str) -> bool:
    lower = text.lower()
    return any(kw in lower for kw in PROBLEM_KEYWORDS)


def _snapshot_to_signals(snapshot: dict, source_url: str) -> list[dict]:
    """Extract problem-indicating posts from a camofox snapshot.

    Snapshot elements are accessibility nodes. Reddit post titles appear
    as 'link' elements with URLs pointing to reddit.com. We collect links
    whose text matches problem keywords.
    """
    elements = snapshot.get("elements", [])
    page_title = snapshot.get("title", "")
    signals: list[dict] = []

    # Strategy 1: Collect links (post titles) that match problem keywords
    for link in _extract_links(elements):
        if "reddit.com" not in link["url"] and "redd.it" not in link["url"]:
            continue
        if _matches_problem(link["text"]):
            signals.append({
                "title": link["text"][:200],
                "text": link["text"][:2000],
                "url": link["url"],
                "source_type": "reddit",
                "source_tier": 1,
                "discovered_at": datetime.now(timezone.utc).isoformat(),
            })

    # Strategy 2: Collect all text content, look for problem patterns in
    # larger text blocks (post body text, comments, etc.)
    all_texts = _extract_texts(elements)
    combined = " ".join(all_texts)
    if _matches_problem(combined) and not signals:
        # We found problem signal in text but not in individual link titles.
        # Create one signal from the page context.
        signals.append({
            "title": page_title[:200] if page_title else "Reddit post",
            "text": combined[:2000],
            "url": source_url,
            "source_type": "reddit",
            "source_tier": 1,
            "discovered_at": datetime.now(timezone.utc).isoformat(),
        })

    return signals


async def fetch_reddit(settings: "Settings") -> list[dict]:
    """
    Fetch Reddit problem signals via CamoFox stealth browser.

    Strategy:
      1. Navigate to each seed subreddit via @reddit_subreddit macro.
      2. Extract accessibility snapshots, filter for problem keywords.
      3. Run keyword searches via @reddit_search macro.
      4. Deduplicate by URL.

    No API keys. CamoFox provides C++ engine-level anti-detection.
    """
    if not settings.browser_api_url:
        logger.warning("Reddit scraper: browser_api_url not configured, skipping")
        return []

    client = BrowserClient(settings.browser_api_url, f"{settings.browser_user_id}-reddit")
    if not await client.start():
        logger.error("Reddit scraper: failed to connect to browser at %s", settings.browser_api_url)
        return []

    all_signals: list[dict] = []

    try:
        # ── Subreddit pages ────────────────────────────────────────────
        all_subs = list(dict.fromkeys(SEED_SUBREDDITS + INDUSTRY_SUBREDDITS))
        for sub in all_subs:
            snapshot = await client.search(
                "@reddit_subreddit", sub
            )
            if snapshot:
                url = f"https://www.reddit.com/r/{sub}/"
                signals = _snapshot_to_signals(snapshot, url)
                all_signals.extend(signals)
                logger.debug("r/%s: %d signals", sub, len(signals))
            await asyncio.sleep(REQUEST_DELAY)

        # ── Keyword searches ───────────────────────────────────────────
        for query in SEARCH_QUERIES:
            snapshot = await client.search("@reddit_search", query)
            if snapshot:
                url = f"https://www.reddit.com/search/?q={query}"
                signals = _snapshot_to_signals(snapshot, url)
                all_signals.extend(signals)
                logger.debug("search '%s': %d signals", query, len(signals))
            await asyncio.sleep(REQUEST_DELAY)

    finally:
        await client.stop()

    # Deduplicate by URL
    seen: set[str] = set()
    unique: list[dict] = []
    for s in all_signals:
        if s["url"] not in seen:
            seen.add(s["url"])
            unique.append(s)

    logger.info(
        "Reddit: %d unique signals (%d raw) from %d subreddits + %d searches",
        len(unique), len(all_signals), len(all_subs), len(SEARCH_QUERIES),
    )
    return unique
