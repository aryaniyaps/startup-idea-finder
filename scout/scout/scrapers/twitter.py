"""
Twitter/X scraper — CamoFox stealth browser via REST API.
Uses camofox-browser's @twitter_search macro and direct URL navigation.
Zero API keys. C++ engine-level anti-detection.
"""

from __future__ import annotations

import asyncio
import logging
import re
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from scout.scrapers.browser_client import BrowserClient, _extract_texts, _extract_links

if TYPE_CHECKING:
    from scout.config import Settings

logger = logging.getLogger(__name__)

# ── Tracked accounts ────────────────────────────────────────────────────
TRACKED_ACCOUNTS: list[str] = [
    "levelsio",
    "patio11",
    "dhh",
    "sama",
    "naval",
    "paulg",
    "lennysan",
    "shreyas",
    "ycombinator",
    "firstround",
    "a16z",
    "harrisongil",
    "arvidkahl",
    "robfitz",
    "hnshah",
    "garrytan",
    "mwseibel",
]

# ── Keyword searches ────────────────────────────────────────────────────
SEARCH_QUERIES: list[str] = [
    "frustrated with software",
    "someone should build",
    "wish there was an app",
    "manual process workaround",
    "hate this software",
    "looking for a tool",
    "any recommendations for",
    "paying for software",
]

# ── Constants ────────────────────────────────────────────────────────────
REQUEST_DELAY = 2.5
_HTML_STRIP_RE = re.compile(r"<[^>]+>")


def _strip_html(text: str) -> str:
    return _HTML_STRIP_RE.sub(" ", text).strip()


def _truncate(text: str, max_len: int = 80) -> str:
    stripped = text.strip()
    if len(stripped) <= max_len:
        return stripped
    return stripped[: max_len - 1].rstrip() + "\u2026"


def _snapshot_to_signals(snapshot: dict, source_url: str) -> list[dict]:
    """Extract tweets from a camofox accessibility snapshot.

    Twitter/X accessibility snapshots contain tweet text in various roles.
    We extract all text content and link elements.
    """
    elements = snapshot.get("elements", [])
    page_title = snapshot.get("title", "")
    signals: list[dict] = []

    # Collect links (tweet URLs) and their text
    links = _extract_links(elements)
    texts = _extract_texts(elements)

    # Strategy: pair link text with URLs for individual tweets
    for link in links:
        url = link["url"]
        if not url or ("twitter.com" not in url and "x.com" not in url):
            continue
        text = link["text"]
        if text and len(text) > 10:  # skip trivial links
            signals.append({
                "title": _truncate(_strip_html(text), 80),
                "text": _strip_html(text)[:2000],
                "url": url,
                "source_type": "twitter",
                "source_tier": 1,
                "discovered_at": datetime.now(timezone.utc).isoformat(),
            })

    # If no individual tweets found, use page-level text
    if not signals and texts:
        combined = " ".join(texts)
        if len(combined) > 20:
            signals.append({
                "title": _truncate(_strip_html(page_title), 80),
                "text": _strip_html(combined)[:2000],
                "url": source_url,
                "source_type": "twitter",
                "source_tier": 1,
                "discovered_at": datetime.now(timezone.utc).isoformat(),
            })

    return signals


async def fetch_twitter(settings: "Settings", backfill: bool = False) -> list[dict]:
    """
    Fetch Twitter/X problem signals via CamoFox stealth browser.

    Strategy:
      1. Search Twitter via @twitter_search macro for problem keywords.
      2. Navigate to tracked account profile pages directly.
      3. Extract tweet content from accessibility snapshots.

    No API keys or bearer tokens. CamoFox provides C++ engine-level anti-detection
    that prevents Twitter from detecting this as automation.
    """
    if not settings.browser_api_url:
        logger.warning("Twitter scraper: browser_api_url not configured, skipping")
        return []

    client = BrowserClient(settings.browser_api_url, f"{settings.browser_user_id}-twitter", api_key=settings.browser_api_key)
    if not await client.start():
        logger.error("Twitter scraper: failed to connect to browser at %s", settings.browser_api_url)
        return []

    all_signals: list[dict] = []
    request_delay = 0.5 if backfill else REQUEST_DELAY

    try:
        # ── Keyword searches via @twitter_search macro ─────────────────
        for query in SEARCH_QUERIES:
            snapshot = await client.search("@twitter_search", query)
            if snapshot:
                url = f"https://x.com/search?q={query}"
                signals = _snapshot_to_signals(snapshot, url)
                all_signals.extend(signals)
                logger.debug("search '%s': %d signals", query, len(signals))
            await asyncio.sleep(request_delay)

        # ── User profile pages ─────────────────────────────────────────
        # Navigate directly to each user's timeline
        for username in TRACKED_ACCOUNTS:
            snapshot = await client.fetch_page(f"https://x.com/{username}")
            if snapshot:
                signals = _snapshot_to_signals(snapshot, f"https://x.com/{username}")
                all_signals.extend(signals)
                logger.debug("@%s: %d signals", username, len(signals))
            await asyncio.sleep(request_delay)

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
        "Twitter: %d unique signals (%d raw) from %d accounts + %d searches",
        len(unique), len(all_signals), len(TRACKED_ACCOUNTS), len(SEARCH_QUERIES),
    )
    return unique
