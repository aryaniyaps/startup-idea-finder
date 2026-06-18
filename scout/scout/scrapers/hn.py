"""
Hacker News scraper via the Firebase API.

No auth needed — the public Firebase REST API is read-only.
Endpoints:
  /v0/askstories.json   — top Ask HN stories
  /v0/showstories.json  — top Show HN stories
  /v0/newstories.json   — newest stories
  /v0/item/{id}.json    — single item (story, comment, job, poll, etc.)
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import TYPE_CHECKING

import httpx

if TYPE_CHECKING:
    from scout.config import Settings

logger = logging.getLogger(__name__)

HN_BASE = "https://hacker-news.firebaseio.com/v0"
STORY_LIMIT = 50
NEW_STORY_LIMIT = 30
COMMENT_LIMIT = 5

# Problem-indicator keywords for HN story titles.
PROBLEM_KEYWORDS = [
    "ask hn",
    "who is",
    "how do you",
    "looking for",
    "alternative to",
    "any tool",
    "does anyone",
    "wish there was",
    "someone should build",
    "why is there no",
    "recommend",
    "suggest",
    "frustrated",
    "pain point",
    "workaround",
    "hate",
    "broken",
    "gap",
    "missing",
    "need for",
]


def _matches_problem(title: str) -> bool:
    """Check whether a story title contains problem-indicator signals."""
    lower = title.lower()
    return any(kw in lower for kw in PROBLEM_KEYWORDS)


async def _fetch_item(
    client: httpx.AsyncClient, item_id: int, sem: asyncio.Semaphore
) -> dict | None:
    """Fetch a single HN item by id, with concurrency control."""
    async with sem:
        try:
            resp = await client.get(f"{HN_BASE}/item/{item_id}.json")
            resp.raise_for_status()
            return resp.json()
        except Exception as exc:
            logger.debug("HN item %d fetch failed: %s", item_id, exc)
            return None


async def _fetch_top_comments(
    client: httpx.AsyncClient,
    kids: list[int],
    sem: asyncio.Semaphore,
) -> list[dict]:
    """Fetch the top N comments for a story."""
    if not kids:
        return []
    kids = kids[:COMMENT_LIMIT]
    tasks = [_fetch_item(client, kid, sem) for kid in kids]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    comments: list[dict] = []
    for r in results:
        if isinstance(r, dict) and r and not r.get("deleted"):
            comments.append(r)
    return comments


async def fetch_hn(settings: "Settings", backfill: bool = False) -> list[dict]:
    """
    Fetch recent Ask HN, Show HN, and new stories that indicate problems.

    Returns list[dict] with keys:
      title, text, url, source_type, source_tier, discovered_at
    """
    discovered_at = datetime.now(timezone.utc).isoformat()
    sem = asyncio.Semaphore(20)
    story_limit = 200 if backfill else STORY_LIMIT
    new_limit = 100 if backfill else NEW_STORY_LIMIT

    async with httpx.AsyncClient(timeout=30) as client:
        try:
            # Fetch story ID lists.
            resp_ask = await client.get(f"{HN_BASE}/askstories.json")
            resp_ask.raise_for_status()
            ask_ids: list[int] = resp_ask.json()[:story_limit]

            resp_show = await client.get(f"{HN_BASE}/showstories.json")
            resp_show.raise_for_status()
            show_ids: list[int] = resp_show.json()[:story_limit]

            resp_new = await client.get(f"{HN_BASE}/newstories.json")
            resp_new.raise_for_status()
            new_ids: list[int] = resp_new.json()[:new_limit]
        except Exception as exc:
            logger.error("HN API fetch failed for story lists: %s", exc)
            return []

        # Deduplicate IDs (ask/show/new may overlap).
        all_ids: dict[int, str] = {}
        for sid in ask_ids:
            all_ids.setdefault(sid, "ask")
        for sid in show_ids:
            all_ids.setdefault(sid, "show")
        for sid in new_ids:
            all_ids.setdefault(sid, "new")

        # Fetch item details concurrently.
        tasks = {sid: _fetch_item(client, sid, sem) for sid in all_ids}
        items = await asyncio.gather(*tasks.values(), return_exceptions=True)

        signals: list[dict] = []
        for sid, item in zip(tasks.keys(), items):
            if item is None or not isinstance(item, dict):
                continue
            title = (item.get("title") or "").strip()
            if not title:
                continue
            if not _matches_problem(title):
                continue

            text_parts: list[str] = []
            body = (item.get("text") or "").strip()
            if body:
                text_parts.append(body)

            # Fetch top comments.
            kids = item.get("kids") or []
            comments = await _fetch_top_comments(client, kids, sem)
            for c in comments:
                ctext = (c.get("text") or "").strip()
                if ctext:
                    text_parts.append(ctext)

            full_text = "\n\n".join(text_parts)
            item_id = item.get("id", sid)
            hn_url = f"https://news.ycombinator.com/item?id={item_id}"
            source_url = item.get("url") or hn_url

            signals.append({
                "title": title,
                "text": full_text,
                "url": source_url,
                "source_type": "hn",
                "source_tier": 1,
                "discovered_at": discovered_at,
            })

        logger.info("HN: %d signals from %d stories", len(signals), len(tasks))
        return signals
