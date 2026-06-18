"""
GitHub Issues scraper — searches for high-reaction feature requests and bugs.

GitHub Issues are called "gold mines most people ignore" in the ChatGPT
framework. Developer pain is documented in detail with technical context.
Tier 4 source (1.1x multiplier).
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import TYPE_CHECKING

import httpx

from scout.scrapers.base import safe_fetch

if TYPE_CHECKING:
    from scout.config import Settings

logger = logging.getLogger(__name__)

# Popular open-source repositories to search across domains.
TRACKED_REPOS: list[str] = [
    # Web dev
    "facebook/react",
    "vuejs/vue",
    "vercel/next.js",
    "sveltejs/svelte",
    "tailwindlabs/tailwindcss",
    "microsoft/vscode",
    "npm/cli",
    # Data
    "pandas-dev/pandas",
    "pola-rs/polars",
    "duckdb/duckdb",
    "apache/spark",
    # DevOps
    "kubernetes/kubernetes",
    "moby/moby",
    "hashicorp/terraform",
    "ansible/ansible",
    # General / productivity
    "home-assistant/core",
    "obsidianmd/obsidian-releases",
    "logseq/logseq",
    "calcom/cal.com",
    # Python / AI
    "python/cpython",
    "scikit-learn/scikit-learn",
    "pytorch/pytorch",
]

GITHUB_API_SEARCH = "https://api.github.com/search/issues"
MAX_QUERIES_PER_RUN = 10
MAX_RESULTS = 30
MIN_REACTIONS = 20
MIN_COMMENTS = 15
ISSUE_CREATED_AFTER = "2026-01-01"


def _truncate(text: str, max_len: int = 80) -> str:
    stripped = text.strip().replace("\n", " ")
    if len(stripped) <= max_len:
        return stripped
    return stripped[: max_len - 1].rstrip() + "…"


def _has_problem_signal(text: str) -> bool:
    """Check if text contains signals of an unsolved problem."""
    lower = text.lower()
    signals = [
        "feature request", "enhancement", "would be nice", "why can't",
        "missing", "lack of", "should support", "please add", "request:",
        "need this", "blocker", "dealbreaker", "showstopper", "frustrated",
        "annoys me", "drives me crazy", "waste of time", "painful",
        "hacky", "workaround", "kludge", "regression", "breaking",
        "i wish", "it would be great if", "any plans for",
    ]
    return any(s in lower for s in signals)


async def _fetch_issue_comments(
    client: httpx.AsyncClient,
    comments_url: str,
    headers: dict[str, str],
    max_comments: int = 3,
) -> str:
    """Fetch top comments for an issue."""
    try:
        resp = await client.get(
            f"{comments_url}?per_page={max_comments}&sort=created&direction=desc",
            headers=headers,
        )
        if resp.status_code != 200:
            return ""
        comments = resp.json()
        parts: list[str] = []
        for comment in comments[:max_comments]:
            body = comment.get("body", "")
            if body:
                parts.append(body)
        return "\n\n---\n\n".join(parts)
    except Exception:
        return ""


async def _search_repo_issues(
    client: httpx.AsyncClient,
    repo: str,
    headers: dict[str, str],
) -> list[dict]:
    """Search open issues for a single repository."""
    results: list[dict] = []

    query = (
        f"is:issue is:open repo:{repo} "
        f"sort:reactions-+1 "
        f"created:>{ISSUE_CREATED_AFTER}"
    )
    params = {
        "q": query,
        "per_page": 10,
        "sort": "reactions",
        "order": "desc",
    }

    try:
        resp = await client.get(GITHUB_API_SEARCH, headers=headers, params=params)

        if resp.status_code == 403:
            rate_remaining = resp.headers.get("x-ratelimit-remaining", "0")
            if rate_remaining == "0":
                reset_ts = resp.headers.get("x-ratelimit-reset", "0")
                wait = max(int(reset_ts) - int(datetime.now(timezone.utc).timestamp()), 1)
                logger.warning(
                    "GitHub rate limit hit, waiting %ds (repo %r)", wait, repo
                )
                await asyncio.sleep(min(wait, 60))
                return []
            logger.warning("GitHub 403 for repo %r", repo)
            return []

        if resp.status_code != 200:
            logger.debug("GitHub search returned %d for repo %r", resp.status_code, repo)
            return []

        data = resp.json()
    except Exception:
        logger.debug("GitHub search failed for repo %r", repo)
        return []

    for issue in data.get("items", []):
        if len(results) >= MAX_RESULTS:
            break

        reactions = issue.get("reactions", {})
        total_reactions = (
            reactions.get("total_count", 0)
            if isinstance(reactions, dict)
            else 0
        )
        comments_count = issue.get("comments", 0)

        if total_reactions < MIN_REACTIONS and comments_count < MIN_COMMENTS:
            continue

        title = issue.get("title", "")
        body = issue.get("body") or ""
        issue_url = issue.get("html_url", "")
        comments_url = issue.get("comments_url", "")
        labels = [lb.get("name", "") for lb in issue.get("labels", [])]

        if not title or not issue_url:
            continue

        # Fetch top comments for context.
        comments_text = ""
        if comments_url and (total_reactions >= MIN_REACTIONS or comments_count >= MIN_COMMENTS):
            comments_text = await _fetch_issue_comments(client, comments_url, headers)

        full_text = body
        if comments_text:
            full_text = f"{body}\n\n---\nTop comments:\n{comments_text}"

        # Check for problem signals in title, body, labels.
        combined = f"{title} {' '.join(labels)} {body} {comments_text}"
        if not _has_problem_signal(combined):
            continue

        results.append({
            "title": _truncate(title),
            "text": full_text[:2000],  # Cap text length.
            "url": issue_url,
            "source_type": "github_issue",
            "source_tier": 4,
            "discovered_at": datetime.now(timezone.utc).isoformat(),
        })

        await asyncio.sleep(0.2)  # Micro-delay between issues (comment fetch).

    return results


async def fetch_github_issues(settings: Settings) -> list[dict]:
    """Search GitHub Issues for high-reaction feature requests and bugs.

    Queries popular open-source repositories for open issues with high reaction
    counts or comment threads, filtering for problem signals. Handles GitHub
    API rate limits with backoff.

    Returns list[dict] with keys title, text, url, source_type, source_tier,
    discovered_at. Returns [] on failure.
    """
    headers: dict[str, str] = {
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "StartupIdeaScout/1.0",
    }
    if settings.github_token:
        headers["Authorization"] = f"Bearer {settings.github_token}"

    # Limit repos to MAX_QUERIES_PER_RUN to stay within rate limits.
    repos = TRACKED_REPOS[:MAX_QUERIES_PER_RUN]

    timeout = httpx.Timeout(30.0, connect=10.0)
    async with httpx.AsyncClient(timeout=timeout, headers=headers) as client:
        try:
            tasks = [_search_repo_issues(client, repo, headers) for repo in repos]
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)
        except Exception:
            logger.exception("GitHub issues fetch failed")
            return []

    all_issues: list[dict] = []
    for result in batch_results:
        if isinstance(result, list):
            all_issues.extend(result)
        elif isinstance(result, Exception):
            logger.debug("GitHub sub-search failed: %s", result)

    # Deduplicate by URL.
    seen: set[str] = set()
    unique: list[dict] = []
    for issue in all_issues:
        if issue["url"] not in seen:
            seen.add(issue["url"])
            unique.append(issue)

    limited = unique[:MAX_RESULTS]
    logger.info("GitHub Issues: %d qualifying issues found", len(limited))
    return limited
