"""Cache tests recompute expectations from the same artifacts (ground truth
is the parquet, not a hard-coded number), so they survive pipeline re-runs."""
import json

import pandas as pd
import pytest

from app import settings
from app.cache import DataCache


@pytest.fixture(scope="module")
def cache() -> DataCache:
    c = DataCache()
    c.load()
    return c


def test_data_through_matches_series_total(cache):
    s = pd.read_parquet(settings.P3_OUT / "series_total.parquet")
    assert cache.data_through == str(pd.to_datetime(s["date"]).max().date())


def test_flow_daily_sums_to_filtered_bookings(cache):
    be = pd.read_parquet(settings.FEAT / "bookings_enriched.parquet")
    # Artifacts may carry created_date as date objects or strings; normalize
    # to YYYY-MM-DD so string comparison against data_through works.
    be["created_date"] = pd.to_datetime(be["created_date"]).dt.date.astype(str)
    n = int((be["created_date"] <= cache.data_through).sum())
    assert sum(r["bookings"] for r in cache.flow_daily["series"]) == n


def test_revenue_route_sums_to_total(cache):
    assert sum(r["bookings"] for r in cache.revenue["by_route"]) == sum(
        r["bookings"] for r in cache.flow_daily["series"]
    )


def test_forecast_matches_model_meta(cache):
    meta = json.load(open(settings.P3_MODELS / "model_meta_jemmal.json"))
    f = next(x for x in cache.forecast["forecasts"] if x["station"] == "jemmal")
    assert f["forecast"][0]["yhat"] == meta["forecast"][0]
    assert f["model"] == meta["model"]


def test_anomalies_match_summary(cache):
    d = json.load(open(settings.P3_OUT / "anomaly_summary.json"))
    expected = sum(len(d[k]["flag_days"]) for k in settings.KEYS)
    assert len(cache.anomalies["anomalies"]) == expected


def test_reload_keeps_invariants(cache):
    cache.reload()
    be = pd.read_parquet(settings.FEAT / "bookings_enriched.parquet")
    be["created_date"] = pd.to_datetime(be["created_date"]).dt.date.astype(str)
    assert sum(r["bookings"] for r in cache.flow_daily["series"]) == int(
        (be["created_date"] <= cache.data_through).sum()
    )
