import httpx
import asyncio
import logging

logger = logging.getLogger(__name__)


async def safe_fetch(
    client: httpx.AsyncClient,
    url: str,
    max_retries: int = 3,
    **kwargs,
) -> str:
    """Fetch URL with retry and exponential backoff.

    Returns response text on success, empty string on permanent failure.
    Callers inject their own httpx.AsyncClient.
    """
    kwargs.setdefault("timeout", 30)
    last_exc: Exception | None = None

    for attempt in range(max_retries):
        try:
            resp = await client.get(url, **kwargs)
            resp.raise_for_status()
            return resp.text
        except httpx.HTTPStatusError as exc:
            last_exc = exc
            status = exc.response.status_code
            if 400 <= status < 500:
                logger.warning("safe_fetch %s → HTTP %d (client error, not retrying)", url, status)
                return ""
            logger.warning(
                "safe_fetch %s → HTTP %d (attempt %d/%d)",
                url, status, attempt + 1, max_retries,
            )
        except (httpx.RequestError, asyncio.TimeoutError) as exc:
            last_exc = exc
            logger.warning(
                "safe_fetch %s → %s: %s (attempt %d/%d)",
                url, type(exc).__name__, exc, attempt + 1, max_retries,
            )

        if attempt < max_retries - 1:
            delay = 2 ** attempt
            await asyncio.sleep(delay)

    logger.error("safe_fetch %s → all %d retries exhausted: %s", url, max_retries, last_exc)
    return ""
