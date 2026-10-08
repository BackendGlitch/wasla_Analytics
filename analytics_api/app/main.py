"""Read-only analytics API (Phase 5).

REST endpoints serve the in-memory cache; the WS feed (see live.py)
broadcasts minutely live counts. Never writes to production DBs.
"""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from . import settings
from .cache import DataCache
from .live import LiveFeed, tunnel_status

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("analytics_api")

cache = DataCache()
feed = LiveFeed()


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        cache.load()
    except Exception as e:  # noqa: BLE001 - degraded mode, /api/health explains
        log.exception("cache load failed: %s", e)
    feed.start()
    yield
    feed.stop()


app = FastAPI(title="Wasla Analytics API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:3001",
        "https://wasla-analytics-samers-projects-e0e34ea8.vercel.app",
    ],
    allow_methods=["*"],
    allow_headers=["*"],
)


def _require_cache():
    if cache.loaded_at is None:
        return JSONResponse(
            status_code=503,
            content={"detail": "artifact cache not loaded — see /api/health"},
        )
    return None


@app.get("/api/overview")
def api_overview():
    if err := _require_cache():
        return err
    return cache.overview


@app.get("/api/flow/hourly")
def api_flow_hourly():
    if err := _require_cache():
        return err
    return cache.flow_hourly


@app.get("/api/flow/daily")
def api_flow_daily():
    if err := _require_cache():
        return err
    return cache.flow_daily


@app.get("/api/revenue")
def api_revenue():
    if err := _require_cache():
        return err
    return cache.revenue


@app.get("/api/routes")
def api_routes():
    if err := _require_cache():
        return err
    return cache.routes


@app.get("/api/fleet")
def api_fleet():
    if err := _require_cache():
        return err
    return cache.fleet


@app.get("/api/forecast")
def api_forecast():
    if err := _require_cache():
        return err
    return cache.forecast


@app.get("/api/anomalies")
def api_anomalies():
    if err := _require_cache():
        return err
    return cache.anomalies


@app.get("/api/health")
def api_health():
    return {
        "status": "ok" if cache.loaded_at else "degraded",
        "cache_loaded_at": cache.loaded_at,
        "artifacts_path": str(settings.REPO),
        "tunnels": tunnel_status(),
    }


@app.post("/api/refresh", status_code=204)
def api_refresh():
    cache.reload()
    return None


@app.websocket("/ws/live")
async def ws_live(websocket: WebSocket):
    await feed.connect(websocket)
