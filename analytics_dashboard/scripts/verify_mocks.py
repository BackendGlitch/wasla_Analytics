#!/usr/bin/env python3
"""Independently re-sum the artifacts and diff against public/mock/*.json.

This is the traceability gate: every number the dashboard can render in
mock mode must equal a value recomputed here from the parquet/JSON
artifacts. Run after every gen_mocks.py.

Run: python3 scripts/verify_mocks.py   (exit 1 on any mismatch)
"""
import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
REPO = ROOT.parent
MOCK = ROOT / "public" / "mock"
FEAT = REPO / "Phase_1" / "data" / "features"
CLEAN = REPO / "Phase_1" / "data" / "clean"
P2_OUT = REPO / "Phase_2" / "output"
P3_MODELS = REPO / "Phase_3" / "models"
P3_OUT = REPO / "Phase_3" / "output"

STATIONS = ["jemmal", "monastir"]
KEYS = ["jemmal", "monastir", "total"]
FEE = 0.15
FAILURES: list[str] = []


def check(name: str, cond: bool, detail: str = "") -> None:
    if cond:
        print(f"  ok  {name}")
    else:
        FAILURES.append(name)
        print(f"FAIL  {name} {detail}")


def load_be() -> pd.DataFrame:
    be = pd.read_parquet(FEAT / "bookings_enriched.parquet")
    # Match gen_mocks.py: normalize created_date to YYYY-MM-DD strings.
    be["created_date"] = pd.to_datetime(be["created_date"]).dt.date.astype(str)
    be["is_real"] = be["is_ghost"].eq(0)
    be["station_fee"] = be["seats"] * FEE
    be["real_rev"] = be["rev"].where(be["is_real"], 0.0)
    return be


def data_through() -> str:
    s = pd.read_parquet(P3_OUT / "series_total.parquet")
    return str(pd.to_datetime(s["date"]).max().date())


def main() -> None:
    be = load_be()
    dt = data_through()
    sub = be[be["created_date"].le(dt)]

    # ---- overview ----
    o = json.load(open(MOCK / "overview.json"))
    check("overview.data_through", o["data_through"] == dt, f"{o['data_through']} != {dt}")
    for st in STATIONS:
        day = sub[(sub["station"] == st) & (sub["created_date"] == dt)]
        s = o["stations"][st]
        check(f"overview.{st}.bookings_latest_day", s["bookings_latest_day"] == len(day))
        check(f"overview.{st}.revenue_passenger_paid_latest_day",
              abs(s["revenue_passenger_paid_latest_day"] - float(day["rev"].sum())) < 0.01)
        check(f"overview.{st}.revenue_station_fee_latest_day",
              abs(s["revenue_station_fee_latest_day"] - float(day["station_fee"].sum())) < 0.01)
        check(f"overview.{st}.real/ghost sum",
              s["real_bookings_latest_day"] + s["ghost_bookings_latest_day"] == len(day))
    check("overview.totals sum",
          o["totals"]["bookings_latest_day"]
          == o["stations"]["jemmal"]["bookings_latest_day"] + o["stations"]["monastir"]["bookings_latest_day"])

    # ---- flow ----
    fh = json.load(open(MOCK / "flow/hourly.json"))
    fd = json.load(open(MOCK / "flow/daily.json"))
    check("flow_hourly total bookings",
          sum(r["bookings"] for r in fh["series"]) == len(sub),
          f"{sum(r['bookings'] for r in fh['series'])} != {len(sub)}")
    check("flow_daily total bookings",
          sum(r["bookings"] for r in fd["series"]) == len(sub))
    per_st = sub.groupby("station").size()
    for st in STATIONS:
        got = sum(r["bookings"] for r in fd["series"] if r["station"] == st)
        check(f"flow_daily.{st} bookings", got == int(per_st[st]), f"{got} != {per_st[st]}")

    # ---- revenue ----
    r = json.load(open(MOCK / "revenue.json"))
    check("revenue.daily passenger_paid total",
          abs(sum(x["passenger_paid"] for x in r["daily"]) - float(sub["rev"].sum())) < 1.0)
    for x in r["real_vs_ghost"]:
        check(f"revenue.real_vs_ghost {x['date']} sums",
              abs((x["real"] + x["ghost"]) - next(
                  d["passenger_paid"] for d in r["daily"] if d["created_date"] == x["date"]
              )) < 0.01)
    check("revenue.by_route bookings total",
          sum(x["bookings"] for x in r["by_route"]) == len(sub))

    # ---- routes ----
    rt = json.load(open(MOCK / "routes.json"))
    check("routes bookings total", sum(x["bookings"] for x in rt["routes"]) == len(sub))

    # ---- fleet ----
    fl = json.load(open(MOCK / "fleet.json"))
    fs = json.load(open(P2_OUT / "fleet_stats.json"))
    for st in STATIONS:
        check(f"fleet.summary.{st} == fleet_stats.json",
              fl["summary"][st]["avg_load_factor"] == fs[st]["avg_load_factor"]
              and fl["summary"][st]["active_vehicles"] == fs[st]["vehicles_seen"])
    trips = pd.read_parquet(CLEAN / "trips.parquet")
    trips["date"] = pd.to_datetime(trips["start_time"]).dt.date.astype(str)
    check("fleet.daily trips <= clean trips",
          sum(x["trips"] for x in fl["daily"]) <= len(trips[trips["date"].le(dt)]))

    # ---- forecast ----
    fc = json.load(open(MOCK / "forecast.json"))
    for key in KEYS:
        meta = json.load(open(P3_MODELS / f"model_meta_{key}.json"))
        s = next(x for x in fc["forecasts"] if x["station"] == key)
        lo = meta.get("lo") or meta["forecast"]
        check(f"forecast.{key} yhat", s["forecast"][0]["yhat"] == meta["forecast"][0])
        check(f"forecast.{key} lo", s["forecast"][0]["lo"] == lo[0])
        check(f"forecast.{key} model", s["model"] == meta["model"])

    # ---- anomalies ----
    an = json.load(open(MOCK / "anomalies.json"))
    ans = json.load(open(P3_OUT / "anomaly_summary.json"))
    expected = sum(len(ans[k]["flag_days"]) for k in KEYS)
    check("anomalies count", len(an["anomalies"]) == expected,
          f"{len(an['anomalies'])} != {expected}")

    print()
    if FAILURES:
        print(f"{len(FAILURES)} FAILURES:", ", ".join(FAILURES))
        sys.exit(1)
    print("ALL CHECKS PASSED")


if __name__ == "__main__":
    main()
