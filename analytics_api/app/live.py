"""Minutely live feed (Phase 5).

A background thread polls each station DB with LIGHTWEIGHT count/sum
queries (never the 25-minute extraction) and broadcasts one tick per
TICK_SECONDS to every connected WebSocket. If a station is unreachable
the tick marks that station null and `live` reflects the degraded state —
the feed never crashes.
"""
import asyncio
import logging
import threading
from datetime import datetime, timezone
from typing import Awaitable, Callable

import sqlalchemy as sa

from . import settings

log = logging.getLogger("analytics_api.live")

LIVE_SQL = """
SELECT
  COUNT(*)                                             AS bookings_today,
  COUNT(*) FILTER (WHERE NOT is_ghost_booking)         AS real,
  COUNT(*) FILTER (WHERE is_ghost_booking)             AS ghost,
  COALESCE(SUM(total_amount), 0)                       AS revenue_passenger_paid
FROM bookings
WHERE created_at::date = CURRENT_DATE
"""


def tunnel_status() -> dict:
    """Are the tunnel endpoints configured? (Actual reachability is checked
    per tick; this reports configuration + last known state.)"""
    return {
        "jemmal": settings.JEM_DB_URL is not None,
        "monastir": settings.MON_DB_URL is not None,
    }


def _query_station(url: str) -> dict:
    """One cheap aggregate query. Raises on any connection problem."""
    engine = sa.create_engine(url, pool_pre_ping=True, connect_args={"connect_timeout": 5})
    try:
        with engine.connect() as conn:
            row = conn.execute(sa.text(LIVE_SQL)).mappings().one()
        return {
            "bookings_today": int(row["bookings_today"]),
            "revenue_passenger_paid": float(row["revenue_passenger_paid"]),
            "real": int(row["real"]),
            "ghost": int(row["ghost"]),
            "anomaly_flag": False,  # set by the API cache at tick time when a flag exists for today
        }
    finally:
        engine.dispose()


def build_tick(feed: "LiveFeed", pollers: dict[str, Callable[[], dict]]) -> dict:
    """Poll every station; per-station failure -> null entry, not a crash."""
    now = datetime.now(timezone.utc)
    stations = {}
    any_alive = False
    for st, poll in pollers.items():
        try:
            stations[st] = poll()
            any_alive = True
        except Exception as e:  # noqa: BLE001 - graceful degradation is the feature
            log.warning("live poll failed for %s: %s", st, e)
            stations[st] = None
    feed.last_seen = now.isoformat() if any_alive else feed.last_seen
    return {
        "type": "tick",
        "at": now.isoformat(),
        "live": any_alive,
        "last_seen": feed.last_seen,
        "stations": stations,
    }


class LiveFeed:
    def __init__(self) -> None:
        self.last_seen: str | None = None
        self._clients: set = set()
        self._loop: asyncio.AbstractEventLoop | None = None
        self._thread: threading.Thread | None = None
        self._stop = threading.Event()

    # ---- websocket plumbing (runs on the event loop) ----
    async def connect(self, websocket) -> None:
        await websocket.accept()
        # Capture uvicorn's loop: the ticker thread schedules broadcasts here.
        # (Starlette websockets are bound to the loop that accepted them.)
        self._loop = asyncio.get_running_loop()
        self._clients.add(websocket)
        try:
            while True:
                await websocket.receive_text()  # raises on client disconnect
        except Exception:  # noqa: BLE001 - client went away
            pass
        finally:
            self._clients.discard(websocket)

    def _broadcast(self, tick: dict) -> None:
        if not self._clients or self._loop is None:
            return
        import json

        payload = json.dumps(tick)

        async def send_all():
            dead = []
            for ws in list(self._clients):
                try:
                    await ws.send_text(payload)
                except Exception:  # noqa: BLE001
                    dead.append(ws)
            for ws in dead:
                self._clients.discard(ws)

        asyncio.run_coroutine_threadsafe(send_all(), self._loop)

    # ---- ticker thread ----
    def _pollers(self) -> dict:
        pollers = {}
        if settings.JEM_DB_URL:
            pollers["jemmal"] = lambda: _query_station(settings.JEM_DB_URL)
        if settings.MON_DB_URL:
            pollers["monastir"] = lambda: _query_station(settings.MON_DB_URL)
        return pollers

    def _run(self) -> None:
        while not self._stop.is_set():
            tick = build_tick(self, self._pollers())
            self._broadcast(tick)
            self._stop.wait(settings.TICK_SECONDS)

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        thread = threading.Thread(target=self._run, daemon=True, name="live-ticker")
        thread.start()
        self._thread = thread
        log.info("live ticker started (every %ss)", settings.TICK_SECONDS)

    def stop(self) -> None:
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=2)
        log.info("live ticker stopped")
