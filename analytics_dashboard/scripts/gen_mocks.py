#!/usr/bin/env python3
"""Regenerate public/mock/*.json from the Phase 1-3 artifacts.

Every value is recomputed from bookings_enriched.parquet (cut at
data_through = max date of Phase_3 series_total.parquet) plus the
Phase 2/3 output JSONs, so the dashboard tells one consistent story.
The FastAPI service (analytics_api/app/cache.py) mirrors this logic —
change one, change the other.

Run: python3 scripts/gen_mocks.py
"""
import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent          # analytics_dashboard/
REPO = ROOT.parent                                      # Internship/
MOCK = ROOT / "public" / "mock"
FEAT = REPO / "Phase_1" / "data" / "features"
CLEAN = REPO / "Phase_1" / "data" / "clean"
P2_OUT = REPO / "Phase_2" / "output"
P3_MODELS = REPO / "Phase_3" / "models"
P3_OUT = REPO / "Phase_3" / "output"

STATIONS = ["jemmal", "monastir"]
KEYS = ["jemmal", "monastir", "total"]
STATION_FEE_PER_SEAT = 0.15


def write(name: str, obj: dict) -> None:
    target = MOCK / f"{name}.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    with open(target, "w") as f:
        json.dump(obj, f, indent=2)
    print(f"  mock/{name}.json")


def recs(df: pd.DataFrame) -> list:
    """DataFrame -> JSON-safe records (handles numpy types, NaN -> null)."""
    return json.loads(df.to_json(orient="records"))


def load_be() -> pd.DataFrame:
    be = pd.read_parquet(FEAT / "bookings_enriched.parquet")
    be["created_at"] = pd.to_datetime(be["created_at"])
    # Artifacts may carry created_date as date objects or strings; normalize
    # to YYYY-MM-DD so string comparison against data_through works.
    be["created_date"] = pd.to_datetime(be["created_date"]).dt.date.astype(str)
    be["is_real"] = be["is_ghost"].eq(0)
    be["station_fee"] = be["seats"] * STATION_FEE_PER_SEAT
    be["real_rev"] = be["rev"].where(be["is_real"], 0.0)
    return be


def data_through() -> str:
    s = pd.read_parquet(P3_OUT / "series_total.parquet")
    return str(pd.to_datetime(s["date"]).max().date())


def overview(be: pd.DataFrame, dt: str) -> None:
    fleet = json.load(open(P2_OUT / "fleet_stats.json"))
    trips = pd.read_parquet(CLEAN / "trips.parquet")
    trips["date"] = pd.to_datetime(trips["start_time"]).dt.date.astype(str)
    trips_day = trips[trips["date"].eq(dt)].groupby("station").size()
    anomalies = json.load(open(P3_OUT / "anomaly_summary.json"))

    stations, anomaly_today = {}, {}
    for st in STATIONS:
        day = be[(be["station"].eq(st)) & (be["created_date"].eq(dt))]
        stations[st] = {
            "bookings_latest_day": int(len(day)),
            "revenue_passenger_paid_latest_day": float(day["rev"].sum()),
            "revenue_station_fee_latest_day": float(day["station_fee"].sum()),
            "real_bookings_latest_day": int(day["is_real"].sum()),
            "ghost_bookings_latest_day": int((~day["is_real"]).sum()),
            "active_vehicles": fleet[st]["vehicles_seen"],
            "trips_latest_day": int(trips_day.get(st, 0)),
        }
        flag = next((x for x in anomalies[st]["flag_days"] if x["date"] == dt), None)
        anomaly_today[st] = (
            {
                "date": flag["date"],
                "bookings": flag["bookings"],
                "detectors": [k for k in ("rolling_z", "wow_z", "iso") if flag.get(k)],
                "zero_day": flag["zero_day"],
            }
            if flag
            else None
        )

    totals: dict = {
        "bookings_latest_day": sum(s["bookings_latest_day"] for s in stations.values()),
        "revenue_passenger_paid_latest_day": sum(
            s["revenue_passenger_paid_latest_day"] for s in stations.values()
        ),
        "revenue_station_fee_latest_day": sum(
            s["revenue_station_fee_latest_day"] for s in stations.values()
        ),
        "real_bookings_latest_day": sum(s["real_bookings_latest_day"] for s in stations.values()),
        "ghost_bookings_latest_day": sum(s["ghost_bookings_latest_day"] for s in stations.values()),
        "active_vehicles": sum(s["active_vehicles"] for s in stations.values()),
        "trips_latest_day": sum(s["trips_latest_day"] for s in stations.values()),
    }
    write("overview", {"data_through": dt, "totals": totals, "stations": stations, "anomaly_today": anomaly_today})


def flow(be: pd.DataFrame, dt: str) -> None:
    sub = be[be["created_date"].le(dt)]
    hourly = (
        sub.groupby(["station", "hour"], as_index=False)
        .agg(bookings=("id", "count"), seats=("seats", "sum"), revenue_station_fee=("station_fee", "sum"))
        .sort_values(["station", "hour"])
    )
    daily = (
        sub.groupby(["station", "created_date"], as_index=False)
        .agg(
            bookings=("id", "count"),
            seats=("seats", "sum"),
            revenue_passenger_paid=("rev", "sum"),
            revenue_station_fee=("station_fee", "sum"),
            real_bookings=("is_real", "sum"),
        )
        .sort_values(["station", "created_date"])
    )
    daily["ghost_bookings"] = daily["bookings"] - daily["real_bookings"]
    write("flow/hourly", {"data_through": dt, "series": recs(hourly)})
    write("flow/daily", {"data_through": dt, "series": recs(daily)})


def revenue(be: pd.DataFrame, dt: str) -> None:
    sub = be[be["created_date"].le(dt)]
    daily = (
        sub.groupby("created_date", as_index=False)
        .agg(
            passenger_paid=("rev", "sum"),
            station_fee=("station_fee", "sum"),
            real_passenger_paid=("real_rev", "sum"),
        )
        .sort_values("created_date")
    )
    rg = (
        sub.groupby("created_date", as_index=False)
        .agg(passenger_paid=("rev", "sum"), real=("real_rev", "sum"))
        .sort_values("created_date")
    )
    rg["ghost"] = rg["passenger_paid"] - rg["real"]
    by_route = (
        sub.groupby(["station", "destination_canonical"], as_index=False)
        .agg(
            bookings=("id", "count"),
            revenue_passenger_paid=("rev", "sum"),
            revenue_station_fee=("station_fee", "sum"),
            ghost=("is_ghost", "sum"),
        )
        .sort_values(["station", "bookings"], ascending=[True, False])
    )
    by_route["avg_ticket"] = by_route["revenue_passenger_paid"] / by_route["bookings"]
    by_route["ghost_rate"] = by_route["ghost"] / by_route["bookings"]
    write(
        "revenue",
        {
            "data_through": dt,
            "daily": recs(daily),
            "real_vs_ghost": recs(rg[["created_date", "real", "ghost"]].rename(columns={"created_date": "date"})),
            "by_route": recs(by_route.drop(columns=["ghost"])),
        },
    )


def routes(be: pd.DataFrame, dt: str) -> None:
    sub = be[be["created_date"].le(dt)]
    rt = (
        sub.groupby(["station", "destination_canonical"], as_index=False)
        .agg(
            bookings=("id", "count"),
            revenue_passenger_paid=("rev", "sum"),
            revenue_station_fee=("station_fee", "sum"),
            ghost=("is_ghost", "sum"),
        )
        .sort_values(["station", "bookings"], ascending=[True, False])
    )
    rt["avg_ticket"] = rt["revenue_passenger_paid"] / rt["bookings"]
    rt["ghost_rate"] = rt["ghost"] / rt["bookings"]
    groups = sorted(sub["destination_group"].dropna().unique().tolist())
    write("routes", {"data_through": dt, "groups": groups, "routes": recs(rt.drop(columns=["ghost"]))})


def fleet(dt: str) -> None:
    stats = json.load(open(P2_OUT / "fleet_stats.json"))
    trips = pd.read_parquet(CLEAN / "trips.parquet")
    trips["start_time"] = pd.to_datetime(trips["start_time"])
    trips["seats_combined"] = trips["seats_booked"].fillna(trips["booked_seats"])
    trips["load_factor"] = trips["seats_combined"] / trips["vehicle_capacity"].replace(0, pd.NA)
    trips["date"] = trips["start_time"].dt.date.astype(str)
    trips = trips[trips["date"].le(dt)]
    daily = (
        trips.groupby(["station", "date"], as_index=False)
        .agg(trips=("start_time", "count"), load_factor=("load_factor", "mean"))
        .sort_values(["station", "date"])
    )
    summary = {}
    for st in STATIONS:
        x = stats[st]
        summary[st] = {
            "active_vehicles": x["vehicles_seen"],
            "trips_per_vehicle": x["trips_per_vehicle"],
            "avg_load_factor": x["avg_load_factor"],
            "capacity_coverage_pct": x["load_factor_coverage"],
        }
    write(
        "fleet",
        {
            "data_through": dt,
            "caveat": "Indicative: Monastir trips carry vehicle capacity on ~33% of rows.",
            "summary": summary,
            "daily": recs(daily),
        },
    )


def forecast() -> None:
    metrics = json.load(open(P3_OUT / "model_metrics_v2.json"))
    forecasts, pva = [], []
    for key in KEYS:
        meta = json.load(open(P3_MODELS / f"model_meta_{key}.json"))
        model = meta["model"]
        m = metrics[key]["models"].get(model, {})
        lo = meta.get("lo") or meta["forecast"]
        hi = meta.get("hi") or meta["forecast"]
        pts = [
            {"date": d, "yhat": y, "lo": l, "hi": h}
            for d, y, l, h in zip(meta["horizon_dates"], meta["forecast"], lo, hi)
        ]
        forecasts.append(
            {
                "station": key,
                "model": model,
                "mape": m.get("mape_mean"),
                "mape_std": m.get("mape_std"),
                "horizon_days": meta["horizon_days"],
                "forecast": pts,
            }
        )
        # Honest predicted-vs-actual for rule-based winners only
        # (naive: t-1, seasonal_naive: t-7). SARIMA in-sample predictions are
        # not persisted; the UI omits the comparison for such keys.
        if model in ("naive", "seasonal_naive"):
            s = pd.read_parquet(P3_OUT / f"series_{key}.parquet").set_index("date")["bookings"]
            lag = 1 if model == "naive" else 7
            tail = s.tail(14 + lag)
            for i in range(lag, len(tail)):
                pva.append(
                    {
                        "station": key,
                        "date": str(tail.index[i]),
                        "actual": float(tail.iloc[i]),
                        "predicted": float(tail.iloc[i - lag]),
                    }
                )
    write(
        "forecast",
        {
            "data_through": data_through(),
            "disclaimer": "Forecast volume includes ghost/draft bookings. "
            "Revenue must be evaluated on real bookings only.",
            "forecasts": forecasts,
            "pred_vs_actual": pva,
        },
    )


def anomalies() -> None:
    d = json.load(open(P3_OUT / "anomaly_summary.json"))
    rows = []
    for key in KEYS:
        for f in d[key]["flag_days"]:
            rows.append(
                {
                    "date": f["date"],
                    "station": key,
                    "bookings": f["bookings"],
                    "detectors": [k for k in ("rolling_z", "wow_z", "iso") if f.get(k)],
                    "zero_day": f["zero_day"],
                }
            )
    rows.sort(key=lambda r: (r["date"], r["station"]))
    write("anomalies", {"data_through": data_through(), "anomalies": rows})


def main() -> None:
    be = load_be()
    dt = data_through()
    print(f"data_through: {dt}")
    overview(be, dt)
    flow(be, dt)
    revenue(be, dt)
    routes(be, dt)
    fleet(dt)
    forecast()
    anomalies()
    print("mocks written to", MOCK)


if __name__ == "__main__":
    main()
