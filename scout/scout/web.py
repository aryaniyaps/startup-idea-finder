"""FastAPI dashboard with WebSocket push for live idea updates."""

from __future__ import annotations

import asyncio
import json
import logging
from pathlib import Path

from fastapi import FastAPI, Query, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from scout.config import Settings
from scout.db import Database

logger = logging.getLogger(__name__)

TEMPLATES_DIR = Path(__file__).parent / "templates"

settings = Settings()
db = Database(settings.db_path)
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

app = FastAPI(title="Scout Dashboard", version="1.0.0")

_ws_clients: set[WebSocket] = set()


@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    stats = db.get_stats()
    ideas = db.get_ideas(limit=50)
    return templates.TemplateResponse(
        request, "index.html", {"request": request, "stats": stats, "ideas": ideas}
    )


@app.get("/api/ideas")
async def api_ideas(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    min_score: int = Query(0, ge=0, le=100),
    verdict: str | None = Query(None),
):
    ideas = db.get_ideas(limit=limit, offset=offset, min_score=min_score, verdict=verdict)
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
