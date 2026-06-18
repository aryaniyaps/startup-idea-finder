"""FastAPI API server with WebSocket push for live updates. Serves Vite React SPA in production."""

from __future__ import annotations

import asyncio
import json
import logging
import os
from pathlib import Path

from fastapi import FastAPI, Query, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from scout.config import Settings
from scout.db import Database

logger = logging.getLogger(__name__)

settings = Settings()
db = Database(settings.db_path)

app = FastAPI(title="Scout API", version="2.0.0")

_ws_clients: set[WebSocket] = set()

# ---------------------------------------------------------------------------
# Vite SPA serving (production only — in dev, Vite dev server proxies to us)
# ---------------------------------------------------------------------------
_WEB_DIST = os.environ.get(
    "WEB_DIST_PATH",
    str(Path(__file__).parent.parent.parent / "web" / "dist"),
)


def _spa_enabled() -> bool:
    return os.path.isdir(_WEB_DIST) and os.path.isfile(
        os.path.join(_WEB_DIST, "index.html")
    )


# ---------------------------------------------------------------------------
# Ideas API
# ---------------------------------------------------------------------------


@app.get("/api/ideas")
async def api_ideas(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    min_score: int = Query(0, ge=0, le=100),
    verdict: str | None = Query(None),
):
    ideas = db.get_ideas(
        limit=limit, offset=offset, min_score=min_score, verdict=verdict
    )
    stats = db.get_stats()
    return {"ideas": ideas, "stats": stats}


@app.get("/api/idea/{idea_id}")
async def api_idea_detail(idea_id: str):
    detail = db.get_idea_detail(idea_id)
    if detail is None:
        return {"error": "not found"}, 404
    return detail


@app.get("/api/stats")
async def api_stats():
    return db.get_stats()


# ---------------------------------------------------------------------------
# Signals API
# ---------------------------------------------------------------------------


@app.get("/api/signals")
async def api_signals(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    source_type: str | None = Query(None),
    min_tier: int | None = Query(None),
):
    signals = db.get_signals(
        limit=limit, offset=offset, source_type=source_type, min_tier=min_tier
    )
    stats = db.get_signal_stats()
    return {"signals": signals, "stats": stats}


@app.get("/api/signals/stats")
async def api_signals_stats():
    return db.get_signal_stats()


# ---------------------------------------------------------------------------
# Derived Problems API
# ---------------------------------------------------------------------------


@app.get("/api/problems")
async def api_problems(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    problems = db.get_derived_problems(limit=limit, offset=offset)
    return {"problems": problems}


@app.get("/api/problem/{problem_id}")
async def api_problem_detail(problem_id: str):
    problems = db.get_derived_problems(limit=1, offset=0)
    # Filter by id (simple approach — could add dedicated query)
    for p in problems:
        if p.get("id") == problem_id:
            return p
    return {"error": "not found"}, 404


# ---------------------------------------------------------------------------
# WebSocket
# ---------------------------------------------------------------------------


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    _ws_clients.add(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        _ws_clients.discard(websocket)


async def broadcast_stats(stats: dict):
    payload = json.dumps({"type": "stats", "data": stats})
    dead: list[WebSocket] = []
    for ws in _ws_clients:
        try:
            await ws.send_text(payload)
        except Exception:
            dead.append(ws)
    for ws in dead:
        _ws_clients.discard(ws)


async def broadcast_new_ideas(ideas: list[dict]):
    payload = json.dumps({"type": "new_ideas", "data": ideas})
    dead: list[WebSocket] = []
    for ws in _ws_clients:
        try:
            await ws.send_text(payload)
        except Exception:
            dead.append(ws)
    for ws in dead:
        _ws_clients.discard(ws)


# ---------------------------------------------------------------------------
# SPA serving (must be last — catches all unmatched routes)
# ---------------------------------------------------------------------------

if _spa_enabled():
    # Mount assets at /assets (vite build output)
    assets_dir = os.path.join(_WEB_DIST, "assets")
    if os.path.isdir(assets_dir):
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        """Serve the Vite React SPA for all non-API routes."""
        # Don't intercept API routes
        if full_path.startswith("api/") or full_path.startswith("ws"):
            return {"error": "not found"}, 404
        index_path = os.path.join(_WEB_DIST, "index.html")
        if os.path.isfile(index_path):
            return FileResponse(index_path)
        return {"error": "not found"}, 404
