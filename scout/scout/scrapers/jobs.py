"""
Job board scraper — Upwork and Fiverr for recurring, automatable tasks.

The ChatGPT framework identifies job boards as Tier 3: if companies repeatedly
hire for a repetitive task, software may replace it. This is market proof —
money is already being spent. Tier 3 source (1.2x multiplier).
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import TYPE_CHECKING

import httpx
from bs4 import BeautifulSoup, Tag

from scout.scrapers.base import safe_fetch

if TYPE_CHECKING:
    from scout.config import Settings

logger = logging.getLogger(__name__)

# Search queries targeting repetitive, automatable tasks.
SEARCH_QUERIES: list[str] = [
    "data entry",
    "report generation",
    "compliance",
    "content operations",
    "manual testing",
    "lead generation",
    "data scraping",
    "transcription",
    "bookkeeping",
    "inventory management",
]

MAX_RESULTS = 30
UPWORK_SEARCH = "https://www.upwork.com/nx/search/jobs/"
FIVERR_SEARCH = "https://www.fiverr.com/search/gigs"
MIN_SIMILAR_TITLES = 3  # Jobs with similar titles must appear this many times.


def _truncate(text: str, max_len: int = 80) -> str:
    stripped = text.strip().replace("\n", " ")
    if len(stripped) <= max_len:
        return stripped
    return stripped[: max_len - 1].rstrip() + "…"


def _normalize_title(title: str) -> str:
    """Normalize a job title for similarity comparison."""
    return " ".join(title.lower().split())


def _extract_job_cards(soup: BeautifulSoup, source: str) -> list[Tag]:
    """Extract job/gig listing cards from parsed HTML."""
    if source == "upwork":
        return soup.select(
            '[class*="job-tile"], [class*="job-card"], '
            '[data-test*="job"], [class*="JobTile"], '
            'section[class*="job"], article'
        )
    elif source == "fiverr":
        return soup.select(
            '[class*="gig-card"], [class*="gig-wrapper"], '
            '[class*="GigCard"], [class*="listing-card"], '
            'article, .gig-card-layout'
        )
    return []


def _extract_title(card: Tag) -> str:
    """Extract job/gig title from a card."""
    title_selectors = [
        'h2', 'h3', 'h4',
        '[class*="job-title"]',
        '[class*="title"]',
        '[data-test*="title"]',
        'a[class*="title"]',
    ]
    for sel in title_selectors:
        el = card.select_one(sel)
        if el:
            text = el.get_text(" ", strip=True)
            if 3 < len(text) < 200:
                return text
    return ""


def _extract_description(card: Tag) -> str:
    """Extract job/gig description from a card."""
    desc_selectors = [
        '[class*="description"]',
        '[class*="job-description"]',
        '[class*="body"]',
        '[class*="summary"]',
        '[data-test*="description"]',
        'p',
    ]
    for sel in desc_selectors:
        el = card.select_one(sel)
        if el:
            text = el.get_text(" ", strip=True)
            if len(text) > 20:
                return text
    # Fallback: collect all text nodes.
    return card.get_text(" ", strip=True)


def _extract_link(card: Tag, source: str) -> str:
    """Extract the URL link from a job/gig card."""
    link_el = card.select_one("a[href]")
    if not link_el:
        return ""
    href = link_el.get("href", "")
    if not isinstance(href, str):
        return ""
    if href.startswith("http"):
        return href
    if source == "upwork":
        return f"https://www.upwork.com{href}" if href.startswith("/") else href
    elif source == "fiverr":
        return f"https://www.fiverr.com{href}" if href.startswith("/") else href
    return href


def _find_recurring_jobs(cards: list[Tag], source: str) -> list[dict]:
    """Identify job types that appear repeatedly (indicates recurring need)."""
    # Extract title + description for all cards.
    extracted: list[tuple[str, str, str, str]] = []  # (title, description, url, title_key)
    for card in cards:
        title = _extract_title(card)
        desc = _extract_description(card)
        url = _extract_link(card, source)
        if title and desc:
            extracted.append((title, desc, url, _normalize_title(title)))

    if not extracted:
        return []

    # Count occurrences of similar titles.
    title_counts: dict[str, int] = {}
    title_examples: dict[str, tuple[str, str, str]] = {}  # title_key -> (best title, desc, url)
    for title, desc, url, norm in extracted:
        title_counts[norm] = title_counts.get(norm, 0) + 1
        if norm not in title_examples or len(desc) > len(title_examples[norm][1]):
            title_examples[norm] = (title, desc, url)

    results: list[dict] = []
    for norm, count in title_counts.items():
        if count >= MIN_SIMILAR_TITLES:
            title, desc, url = title_examples[norm]
            results.append({
                "title": _truncate(title),
                "text": desc,
                "url": url,
                "source_type": "job_board",
                "source_tier": 3,
                "discovered_at": datetime.now(timezone.utc).isoformat(),
            })

    return results


async def _scrape_upwork(client: httpx.AsyncClient) -> list[dict]:
    """Scrape Upwork job listings for recurring automatable tasks."""
    all_results: list[dict] = []

    for query in SEARCH_QUERIES:
        if len(all_results) >= MAX_RESULTS:
            break

        url = f"{UPWORK_SEARCH}?q={httpx.URL(query).raw_path.decode() if '%' in query else query.replace(' ', '%20')}"
        try:
            text = await safe_fetch(client, url, max_retries=1)
            if not text:
                continue
        except Exception:
            logger.debug("Upwork fetch failed for query %r", query)
            continue

        try:
            soup = BeautifulSoup(text, "html.parser")
        except Exception:
            continue

        cards = _extract_job_cards(soup, "upwork")
        recurring = _find_recurring_jobs(cards, "upwork")
        all_results.extend(recurring)

        await asyncio.sleep(2)  # Polite delay.

    return all_results


async def _scrape_fiverr(client: httpx.AsyncClient) -> list[dict]:
    """Scrape Fiverr gig listings for recurring automatable services."""
    all_results: list[dict] = []

    for query in SEARCH_QUERIES:
        if len(all_results) >= MAX_RESULTS:
            break

        url = f"{FIVERR_SEARCH}?query={query.replace(' ', '%20')}"
        try:
            text = await safe_fetch(client, url, max_retries=1)
            if not text:
                continue
        except Exception:
            logger.debug("Fiverr fetch failed for query %r", query)
            continue

        try:
            soup = BeautifulSoup(text, "html.parser")
        except Exception:
            continue

        cards = _extract_job_cards(soup, "fiverr")
        recurring = _find_recurring_jobs(cards, "fiverr")
        all_results.extend(recurring)

        await asyncio.sleep(2)  # Polite delay.

    return all_results


async def fetch_jobs(settings: Settings, backfill: bool = False) -> list[dict]:
    """Scrape job boards for recurring tasks that could be automated.

    Searches Upwork and Fiverr for job/gig types that appear repeatedly,
    indicating a market need that software could address. Uses polite delays
    (2s between requests). Filters for job types appearing 3+ times.

    Returns list[dict] with keys title, text, url, source_type, source_tier,
    discovered_at. Returns [] on failure or block.
    """
    timeout = httpx.Timeout(30.0, connect=10.0)
    async with httpx.AsyncClient(
        timeout=timeout,
        headers={"User-Agent": "StartupIdeaScout/1.0 (research; contact@example.com)"},
        follow_redirects=True,
    ) as client:
        try:
            upwork, fiverr = await asyncio.gather(
                _scrape_upwork(client),
                _scrape_fiverr(client),
                return_exceptions=True,
            )
        except Exception:
            logger.exception("Job board scraping failed")
            return []

    all_jobs: list[dict] = []
    for result in (upwork, fiverr):
        if isinstance(result, list):
            all_jobs.extend(result)
        elif isinstance(result, Exception):
            logger.warning("Job board sub-scraper failed: %s", result)

    # Deduplicate by URL or title.
    seen: set[str] = set()
    unique: list[dict] = []
    for job in all_jobs:
        key = job["url"] or job["title"]
        if key not in seen:
            seen.add(key)
            unique.append(job)

    max_results = 100 if backfill else MAX_RESULTS
    limited = unique[:max_results]
    logger.info("Job boards: %d recurring job types found", len(limited))
    return limited
