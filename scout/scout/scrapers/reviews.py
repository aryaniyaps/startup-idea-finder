"""
Review site scraper — G2, Capterra, Trustpilot.

Extracts low-rated (< 3 star) reviews from software review sites. These are
explicitly called "startup ideas in disguise" in the ChatGPT framework —
Tier 2 source (1.3x multiplier). Negative reviews often describe unmet needs
in detail because the reviewer has evaluated alternatives.
"""

from __future__ import annotations

import asyncio
import logging
import re
from datetime import datetime, timezone
from typing import TYPE_CHECKING

import httpx
from bs4 import BeautifulSoup, Tag

from scout.scrapers.base import safe_fetch

if TYPE_CHECKING:
    from scout.config import Settings

logger = logging.getLogger(__name__)

# Software categories to scrape across review sites.
CATEGORIES: list[str] = [
    "project-management",
    "crm",
    "payroll",
    "accounting",
    "erp",
    "marketing-automation",
    "email-marketing",
    "customer-support",
    "help-desk",
    "hr",
    "ecommerce",
    "website-builder",
    "analytics",
    "business-intelligence",
    "collaboration",
    "document-management",
    "invoicing",
    "expense-management",
    "inventory-management",
    "scheduling",
    "time-tracking",
    "video-conferencing",
    "lms",
    "cms",
    "form-builder",
    "survey",
    "landing-page",
]

# Major SaaS companies to check on Trustpilot.
TRUSTPILOT_DOMAINS: list[str] = [
    "salesforce.com",
    "hubspot.com",
    "zendesk.com",
    "zoho.com",
    "freshworks.com",
    "monday.com",
    "asana.com",
    "slack.com",
    "atlassian.com",
    "shopify.com",
    "wix.com",
    "squarespace.com",
    "mailchimp.com",
    "activecampaign.com",
    "intercom.com",
    "drift.com",
    "calendly.com",
    "notion.so",
    "airtable.com",
    "clickup.com",
]

MAX_REVIEWS_PER_RUN = 50
RATING_PATTERN = re.compile(r"(\d+(?:\.\d+)?)")
STAR_PATTERN = re.compile(r"star", re.IGNORECASE)


def _truncate(text: str, max_len: int = 80) -> str:
    stripped = text.strip().replace("\n", " ")
    if len(stripped) <= max_len:
        return stripped
    return stripped[: max_len - 1].rstrip() + "…"


def _extract_rating_stars(element: Tag) -> float | None:
    """Try to extract a numeric star rating from a BeautifulSoup element.

    Checks aria-label, data-rating, title attributes, and star icon counts.
    """
    # Check aria-label: "4 out of 5 stars", "Rated 3.5 out of 5"
    for attr in ("aria-label", "data-rating", "title"):
        val = element.get(attr, "")
        if isinstance(val, str) and val:
            match = RATING_PATTERN.search(val)
            if match:
                try:
                    return float(match.group(1))
                except ValueError:
                    pass

    # Count filled star elements.
    star_els = element.select(
        '[class*="star"]:not([class*="empty"]):not([class*="half"]) svg, '
        ".star.filled, .star-full, [data-testid*='star-filled'], "
        "span.star--filled, svg[class*='star']"
    )
    if star_els:
        # Each filled star typically represents 1 point; cap at 5.
        return min(len(star_els), 5.0)

    # Try half-star elements.
    half_els = element.select(
        '[class*="half-star"], .star-half, [data-testid*="star-half"], '
        "span.star--half"
    )
    if half_els:
        return len(half_els) * 0.5

    return None


def _extract_rating_from_text(text: str) -> float | None:
    """Fallback: extract rating from text like '2.5 / 5' or 'Rating: 1'."""
    # Pattern: "X / 5" or "X out of 5"
    match = re.search(r"(\d+(?:\.\d+)?)\s*(?:/|out of)\s*5", text)
    if match:
        return float(match.group(1))
    # Pattern: "Rating: X"
    match = re.search(r"rating\s*:\s*(\d+(?:\.\d+)?)", text, re.IGNORECASE)
    if match:
        return float(match.group(1))
    return None


def _find_review_rating(review_card: Tag) -> float | None:
    """Extract rating from a review card using multiple strategies."""
    # Strategy 1: find star rating element within the card.
    rating_containers = review_card.select(
        '[class*="star"], [class*="rating"], [data-testid*="star"], '
        '[data-testid*="rating"], [aria-label*="star"], [aria-label*="out of"]'
    )
    for container in rating_containers:
        r = _extract_rating_stars(container)
        if r is not None:
            return r

    # Strategy 2: look for text-based ratings.
    all_text = review_card.get_text(" ", strip=True)
    return _extract_rating_from_text(all_text)


def _extract_review_text(review_card: Tag) -> str:
    """Extract the review body text from a card."""
    # Try common selectors for review body.
    body_selectors = [
        '[class*="review-body"]',
        '[class*="review-text"]',
        '[class*="review-content"]',
        '[data-testid="review-body"]',
        '[data-testid="review-text"]',
        '[class*="comment"]',
        '[class*="description"]',
        'p[class*="review"]',
    ]
    for sel in body_selectors:
        el = review_card.select_one(sel)
        if el:
            text = el.get_text(" ", strip=True)
            if len(text) > 20:  # Skip trivial.
                return text

    # Fallback: get all paragraph text.
    paragraphs = review_card.select("p")
    text = " ".join(p.get_text(" ", strip=True) for p in paragraphs)
    if len(text) > 20:
        return text

    # Last resort: full card text.
    return review_card.get_text(" ", strip=True)


def _extract_review_title(review_card: Tag) -> str:
    """Extract the review title from a card."""
    title_selectors = [
        '[class*="review-title"]',
        '[class*="review-header"]',
        'h3', 'h4', 'h5',
        '[data-testid="review-title"]',
        'strong',
    ]
    for sel in title_selectors:
        el = review_card.select_one(sel)
        if el:
            text = el.get_text(" ", strip=True)
            if 3 < len(text) < 200:
                return text
    return ""


async def _scrape_g2_categories(
    client: httpx.AsyncClient,
) -> list[dict]:
    """Scrape G2 category pages for low-rated reviews."""
    results: list[dict] = []

    for category in CATEGORIES:
        if len(results) >= MAX_REVIEWS_PER_RUN:
            break

        url = f"https://www.g2.com/categories/{category}?order=lowest_rated"
        try:
            text = await safe_fetch(client, url, max_retries=1)
            if not text:
                continue
        except Exception:
            logger.debug("G2 fetch failed for category %r", category)
            continue

        try:
            soup = BeautifulSoup(text, "html.parser")
        except Exception:
            continue

        review_cards = soup.select('[class*="review"], [data-testid*="review"], article')
        for card in review_cards:
            if len(results) >= MAX_REVIEWS_PER_RUN:
                break

            rating = _find_review_rating(card)
            if rating is None or rating >= 3.0:
                continue

            title = _extract_review_title(card)
            body = _extract_review_text(card)
            if not body or len(body) < 30:
                continue

            # Try to find the product name being reviewed.
            product_el = card.select_one('[class*="product"], [class*="name"]')
            product = product_el.get_text(" ", strip=True) if product_el else category

            # Try to find a direct link to the review.
            link_el = card.select_one("a[href]")
            review_url = ""
            if link_el:
                href = link_el.get("href", "")
                if isinstance(href, str):
                    review_url = href if href.startswith("http") else f"https://www.g2.com{href}"

            results.append({
                "title": _truncate(f"{product} review: {title}" if title else f"{product} negative review"),
                "text": body,
                "url": review_url or url,
                "source_type": "review",
                "source_tier": 2,
                "discovered_at": datetime.now(timezone.utc).isoformat(),
            })

        await asyncio.sleep(1)  # Polite delay between category pages.

    return results


async def _scrape_capterra_categories(
    client: httpx.AsyncClient,
) -> list[dict]:
    """Scrape Capterra category pages for low-rated reviews."""
    results: list[dict] = []

    for category in CATEGORIES:
        if len(results) >= MAX_REVIEWS_PER_RUN:
            break

        # Capterra URLs use hyphens like G2 but end differently.
        url = f"https://www.capterra.com/{category}-software/?sort=rating"
        try:
            text = await safe_fetch(client, url, max_retries=1)
            if not text:
                continue
        except Exception:
            logger.debug("Capterra fetch failed for category %r", category)
            continue

        try:
            soup = BeautifulSoup(text, "html.parser")
        except Exception:
            continue

        review_cards = soup.select('[class*="review"], [data-testid*="review"], article, .Card')
        for card in review_cards:
            if len(results) >= MAX_REVIEWS_PER_RUN:
                break

            rating = _find_review_rating(card)
            if rating is None or rating >= 3.0:
                continue

            title = _extract_review_title(card)
            body = _extract_review_text(card)
            if not body or len(body) < 30:
                continue

            product = category.replace("-", " ").title()
            link_el = card.select_one("a[href]")
            review_url = ""
            if link_el:
                href = link_el.get("href", "")
                if isinstance(href, str):
                    review_url = href if href.startswith("http") else f"https://www.capterra.com{href}"

            results.append({
                "title": _truncate(f"{product} review: {title}" if title else f"{product} negative review"),
                "text": body,
                "url": review_url or url,
                "source_type": "review",
                "source_tier": 2,
                "discovered_at": datetime.now(timezone.utc).isoformat(),
            })

        await asyncio.sleep(1)

    return results


async def _scrape_trustpilot_companies(
    client: httpx.AsyncClient,
) -> list[dict]:
    """Scrape Trustpilot company review pages for low-rated reviews."""
    results: list[dict] = []

    for domain in TRUSTPILOT_DOMAINS:
        if len(results) >= MAX_REVIEWS_PER_RUN:
            break

        url = f"https://www.trustpilot.com/review/{domain}"
        try:
            text = await safe_fetch(client, url, max_retries=1)
            if not text:
                continue
        except Exception:
            logger.debug("Trustpilot fetch failed for %r", domain)
            continue

        try:
            soup = BeautifulSoup(text, "html.parser")
        except Exception:
            continue

        review_cards = soup.select(
            '[class*="review"], [data-testid*="review"], article, '
            '.styles_reviewCard, .review-card'
        )
        for card in review_cards:
            if len(results) >= MAX_REVIEWS_PER_RUN:
                break

            rating = _find_review_rating(card)
            if rating is None or rating >= 3.0:
                continue

            title = _extract_review_title(card)
            body = _extract_review_text(card)
            if not body or len(body) < 30:
                continue

            company_name = domain.split(".")[0].capitalize()
            link_el = card.select_one("a[href]")
            review_url = ""
            if link_el:
                href = link_el.get("href", "")
                if isinstance(href, str):
                    review_url = href if href.startswith("http") else f"https://www.trustpilot.com{href}"

            results.append({
                "title": _truncate(f"{company_name} review: {title}" if title else f"{company_name} negative review"),
                "text": body,
                "url": review_url or url,
                "source_type": "review",
                "source_tier": 2,
                "discovered_at": datetime.now(timezone.utc).isoformat(),
            })

        await asyncio.sleep(1)

    return results


async def fetch_reviews(settings: Settings, backfill: bool = False) -> list[dict]:
    """Scrape low-rated reviews from G2, Capterra, and Trustpilot.

    Targets software categories relevant to general business needs and major
    SaaS company pages. Filters to reviews with < 3 stars. Limits to 50 total
    reviews per run.

    Returns list[dict] with keys title, text, url, source_type, source_tier,
    discovered_at. Degrades gracefully on parse failures.
    """
    timeout = httpx.Timeout(30.0, connect=10.0)
    async with httpx.AsyncClient(
        timeout=timeout,
        headers={"User-Agent": "StartupIdeaScout/1.0 (research; contact@example.com)"},
        follow_redirects=True,
    ) as client:
        try:
            g2, capterra, trustpilot = await asyncio.gather(
                _scrape_g2_categories(client),
                _scrape_capterra_categories(client),
                _scrape_trustpilot_companies(client),
                return_exceptions=True,
            )
        except Exception:
            logger.exception("Review scraping failed")
            return []

    all_reviews: list[dict] = []
    for result in (g2, capterra, trustpilot):
        if isinstance(result, list):
            all_reviews.extend(result)
        elif isinstance(result, Exception):
            logger.warning("Review sub-scraper failed: %s", result)

    # Deduplicate by URL.
    seen: set[str] = set()
    unique: list[dict] = []
    for r in all_reviews:
        if r["url"] not in seen:
            seen.add(r["url"])
            unique.append(r)

    max_reviews = 200 if backfill else MAX_REVIEWS_PER_RUN
    limited = unique[:max_reviews]
    logger.info("Reviews: %d unique low-rated reviews found", len(limited))
    return limited
