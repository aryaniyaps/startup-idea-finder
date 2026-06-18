"""
Async REST client for CamoFox stealth browser server.

Camofox-browser runs as a separate Docker service exposing a REST API
on port 9377. This client manages tab lifecycle (create → navigate →
snapshot → extract → close) for programmatic web scraping with C++
engine-level anti-detection.

API ref: https://github.com/redf0x1/camofox-browser
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)

# ── Constants ────────────────────────────────────────────────────────────
DEFAULT_TIMEOUT = 30
NAVIGATE_TIMEOUT = 45
SNAPSHOT_TIMEOUT = 15
TAB_CLEANUP_TIMEOUT = 5


class BrowserClient:
    """Async client for camofox-browser REST API.

    Usage:
        client = BrowserClient("http://localhost:9377", "scout-reddit")
        await client.start()
        tab_id = await client.create_tab()
        await client.navigate(tab_id, url="https://old.reddit.com/r/startups/")
        snapshot = await client.snapshot(tab_id)
        # extract data from snapshot.elements...
        await client.close_tab(tab_id)
        await client.stop()
    """

    def __init__(self, api_url: str, user_id: str = "scout"):
        self.api_url = api_url.rstrip("/")
        self.user_id = user_id
        self._client: httpx.AsyncClient | None = None
        self._healthy = False

    # ── Lifecycle ───────────────────────────────────────────────────────

    async def start(self) -> bool:
        """Initialize client and verify browser health."""
        self._client = httpx.AsyncClient(
            timeout=httpx.Timeout(DEFAULT_TIMEOUT),
            headers={"Content-Type": "application/json"},
        )
        healthy = await self.health_check()
        if healthy:
            logger.info("BrowserClient connected to %s (user=%s)", self.api_url, self.user_id)
        else:
            logger.warning("BrowserClient: health check failed for %s", self.api_url)
        return healthy

    async def stop(self) -> None:
        """Close HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None
        self._healthy = False

    async def health_check(self) -> bool:
        """Check if the camofox-browser server is reachable and healthy."""
        try:
            resp = await self._client.get(f"{self.api_url}/health")
            self._healthy = resp.status_code == 200 and resp.json().get("ok", False)
            return self._healthy
        except Exception as e:
            logger.debug("Health check failed: %s", e)
            self._healthy = False
            return False

    # ── Tab lifecycle ───────────────────────────────────────────────────

    async def create_tab(self, url: str | None = None) -> str | None:
        """Create a new browser tab. Returns tab_id or None on failure."""
        body: dict[str, Any] = {"userId": self.user_id}
        if url:
            body["url"] = url

        try:
            resp = await self._client.post(f"{self.api_url}/tabs", json=body)
            if resp.status_code == 200:
                data = resp.json()
                return data.get("tabId")
            logger.warning("create_tab: HTTP %d — %s", resp.status_code, resp.text[:200])
        except Exception as e:
            logger.warning("create_tab error: %s", e)
        return None

    async def navigate(
        self,
        tab_id: str,
        *,
        url: str | None = None,
        macro: str | None = None,
        query: str | None = None,
    ) -> bool:
        """Navigate a tab to a URL or search macro.

        Args:
            tab_id: Tab to navigate.
            url: Direct URL to navigate to.
            macro: Search macro name (e.g. "@reddit_search", "@twitter_search").
            query: Search query for macro navigation.
        """
        body: dict[str, Any] = {"userId": self.user_id}
        if url:
            body["url"] = url
        if macro:
            body["macro"] = macro
        if query:
            body["query"] = query

        try:
            resp = await self._client.post(
                f"{self.api_url}/tabs/{tab_id}/navigate",
                json=body,
                timeout=NAVIGATE_TIMEOUT,
            )
            return resp.status_code == 200
        except Exception as e:
            logger.warning("navigate(%s) error: %s", tab_id, e)
            return False

    async def wait_for_load(
        self, tab_id: str, timeout_ms: int = 5000, wait_for_network: bool = True
    ) -> bool:
        """Wait for page load to complete."""
        try:
            resp = await self._client.post(
                f"{self.api_url}/tabs/{tab_id}/wait",
                json={
                    "userId": self.user_id,
                    "timeout": timeout_ms,
                    "waitForNetwork": wait_for_network,
                },
                timeout=(timeout_ms / 1000) + 5,
            )
            return resp.status_code == 200
        except Exception as e:
            logger.debug("wait_for_load(%s): %s", tab_id, e)
            return False

    async def snapshot(self, tab_id: str) -> dict | None:
        """Get accessibility snapshot of the current page.

        Returns a dict with keys: url, title, elements (list of dicts with
        role, name, value, url, etc.)
        """
        try:
            resp = await self._client.get(
                f"{self.api_url}/tabs/{tab_id}/snapshot",
                params={"userId": self.user_id},
                timeout=SNAPSHOT_TIMEOUT,
            )
            if resp.status_code == 200:
                return resp.json()
            logger.warning("snapshot(%s): HTTP %d", tab_id, resp.status_code)
        except Exception as e:
            logger.warning("snapshot(%s) error: %s", tab_id, e)
        return None

    async def get_content(self, tab_id: str) -> str | None:
        """Extract readable text content from a tab."""
        try:
            resp = await self._client.post(
                f"{self.api_url}/tabs/{tab_id}/extract-structured",
                json={
                    "userId": self.user_id,
                    "schema": {
                        "type": "object",
                        "properties": {
                            "title": {"type": "string"},
                            "content": {"type": "string"},
                            "links": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "text": {"type": "string"},
                                        "url": {"type": "string"},
                                    },
                                },
                            },
                        },
                    },
                },
                timeout=SNAPSHOT_TIMEOUT,
            )
            if resp.status_code == 200:
                return resp.text
        except Exception as e:
            logger.debug("get_content(%s): %s", tab_id, e)
        return None

    async def close_tab(self, tab_id: str) -> bool:
        """Close a browser tab. Fire-and-forget (errors logged, not raised)."""
        try:
            resp = await self._client.delete(
                f"{self.api_url}/tabs/{tab_id}",
                json={"userId": self.user_id},
                timeout=TAB_CLEANUP_TIMEOUT,
            )
            return resp.status_code == 200
        except Exception as e:
            logger.debug("close_tab(%s): %s", tab_id, e)
            return False

    # ── High-level helpers ──────────────────────────────────────────────

    async def fetch_page(self, url: str) -> dict | None:
        """Open a URL, wait for load, return snapshot. Convenience wrapper."""
        tab_id = await self.create_tab(url)
        if not tab_id:
            return None
        try:
            await self.wait_for_load(tab_id)
            return await self.snapshot(tab_id)
        finally:
            await self.close_tab(tab_id)

    async def search(
        self, macro: str, query: str
    ) -> dict | None:
        """Execute a search macro and return the snapshot.

        Args:
            macro: e.g. "@reddit_search", "@twitter_search", "@reddit_subreddit"
            query: Search query or subreddit name.
        """
        tab_id = await self.create_tab()
        if not tab_id:
            return None
        try:
            ok = await self.navigate(tab_id, macro=macro, query=query)
            if not ok:
                return None
            await self.wait_for_load(tab_id)
            return await self.snapshot(tab_id)
        finally:
            await self.close_tab(tab_id)


def _extract_texts(elements: list[dict], roles: set[str] | None = None) -> list[str]:
    """Extract text content from snapshot elements matching given roles.

    Args:
        elements: List of accessibility elements from snapshot.
        roles: Set of ARIA roles to include. None = all text-bearing roles.
    """
    if roles is None:
        roles = {"heading", "link", "text", "paragraph", "listitem", "article"}
    texts: list[str] = []
    for el in elements:
        role = el.get("role", "")
        name = el.get("name", "")
        if role in roles and name:
            texts.append(name.strip())
    return texts


def _extract_links(elements: list[dict]) -> list[dict]:
    """Extract link elements with URLs from snapshot elements."""
    links: list[dict] = []
    for el in elements:
        if el.get("role") == "link":
            url = el.get("url", "")
            name = el.get("name", "")
            if name:
                links.append({"text": name.strip(), "url": url})
    return links
