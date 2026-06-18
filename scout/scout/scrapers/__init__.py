import logging

logger = logging.getLogger(__name__)

# ── Core scrapers (always available) ────────────────────────────────────
from .base import safe_fetch
from .reddit import fetch_reddit
from .hn import fetch_hn
from .news import fetch_news

# ── Extended scrapers — try real module, fallback to stub ───────────────
# The pipeline never breaks: if an implementing file doesn't exist yet,
# the stub logs a warning and returns [].

try:
    from .twitter import fetch_twitter  # noqa: F401
except ImportError:

    async def fetch_twitter(settings):
        logger.warning("fetch_twitter: module not yet implemented, returning []")
        return []


try:
    from .worldmonitor import fetch_worldmonitor  # noqa: F401
except ImportError:

    async def fetch_worldmonitor(settings):
        logger.warning("fetch_worldmonitor: module not yet implemented, returning []")
        return []


try:
    from .reviews import fetch_reviews  # noqa: F401
except ImportError:

    async def fetch_reviews(settings):
        logger.warning("fetch_reviews: module not yet implemented, returning []")
        return []


try:
    from .github import fetch_github_issues  # noqa: F401
except ImportError:

    async def fetch_github_issues(settings):
        logger.warning("fetch_github_issues: module not yet implemented, returning []")
        return []


try:
    from .jobs import fetch_jobs  # noqa: F401
except ImportError:

    async def fetch_jobs(settings):
        logger.warning("fetch_jobs: module not yet implemented, returning []")
        return []


__all__ = [
    "safe_fetch",
    "fetch_reddit",
    "fetch_hn",
    "fetch_news",
    "fetch_twitter",
    "fetch_worldmonitor",
    "fetch_reviews",
    "fetch_github_issues",
    "fetch_jobs",
]
