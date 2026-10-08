"""Endpoint tests: shapes + numbers re-checked against the artifacts."""
import pandas as pd
from fastapi.testclient import TestClient

from app import settings
from app.main import app


def client():
    # lifespan loads the cache from the repo artifacts
    return TestClient(app)


def test_overview_shape_and_sums():
    with client() as c:
        r = c.get("/api/overview")
        assert r.status_code == 200
        d = r.json()
        assert set(d["stations"]) == {"jemmal", "monastir"}
        assert d["totals"]["bookings_latest_day"] == (
            d["stations"]["jemmal"]["bookings_latest_day"]
            + d["stations"]["monastir"]["bookings_latest_day"]
        )
        assert d["data_through"]


def test_flow_hourly_matches_parquet():
    with client() as c:
        r = c.get("/api/flow/hourly")
        assert r.status_code == 200
        d = r.json()
        be = pd.read_parquet(settings.FEAT / "bookings_enriched.parquet")
        # Artifacts may carry created_date as date objects or strings; normalize
        # to YYYY-MM-DD so string comparison against data_through works.
        be["created_date"] = pd.to_datetime(be["created_date"]).dt.date.astype(str)
        n = int((be["created_date"] <= d["data_through"]).sum())
        assert sum(x["bookings"] for x in d["series"]) == n


def test_revenue_route_avg_ticket_plausible():
    with client() as c:
        r = c.get("/api/revenue")
        assert r.status_code == 200
        d = r.json()
        for row in d["by_route"]:
            if row["bookings"] > 0:
                assert row["avg_ticket"] > 0
                assert 0 <= row["ghost_rate"] <= 1


def test_routes_has_groups():
    with client() as c:
        r = c.get("/api/routes")
        assert r.status_code == 200
        d = r.json()
        assert d["groups"]
        assert d["routes"]


def test_unknown_endpoint_is_404():
    with client() as c:
        assert c.get("/api/nope").status_code == 404
