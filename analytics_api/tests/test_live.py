"""Live-feed tests: tick building + graceful degradation, no real DB needed."""
from app.live import LiveFeed, build_tick

STATION_RESULT = {
    "bookings_today": 10,
    "revenue_passenger_paid": 155.5,
    "real": 2,
    "ghost": 8,
    "anomaly_flag": False,
}


def test_build_tick_ok():
    feed = LiveFeed()
    tick = build_tick(feed, {"jemmal": lambda: STATION_RESULT, "monastir": lambda: STATION_RESULT})
    assert tick["live"] is True
    assert tick["stations"]["jemmal"]["bookings_today"] == 10
    assert tick["last_seen"] is not None


def test_build_tick_degrades_when_queries_fail():
    feed = LiveFeed()

    def boom():
        raise RuntimeError("connection refused")

    tick = build_tick(feed, {"jemmal": boom, "monastir": boom})
    assert tick["live"] is False
    assert tick["last_seen"] is None
    assert all(v is None for v in tick["stations"].values())


def test_partial_failure_marks_that_station_only():
    feed = LiveFeed()

    def boom():
        raise RuntimeError("down")

    tick = build_tick(feed, {"jemmal": lambda: STATION_RESULT, "monastir": boom})
    assert tick["stations"]["jemmal"] is not None
    assert tick["stations"]["monastir"] is None
    # one side alive is still live
    assert tick["live"] is True
