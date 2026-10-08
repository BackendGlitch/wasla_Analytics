"""In-memory artifact cache.

Loads the Phase 1-3 artifacts once at startup and precomputes every REST
payload. Logic mirrors analytics_dashboard/scripts/gen_mocks.py — change
one, change the other. Read-only: only pandas reads of parquet/JSON files.
"""
import json
import logging
from datetime import datetime, timezone

import pandas as pd

from . import settings

log = logging.getLogger("analytics_api.cache")


def _recs(df: pd.DataFrame) -> list:
    return json.loads(df.to_json(orient="records"))


class DataCache:
    def __init__(self) -> None:
        self.loaded_at: str | None = None
        self.data_through: str = ""
        self.overview: dict = {}
        self.flow_hourly: dict = {}
        self.flow_daily: dict = {}
        self.revenue: dict = {}
        self.routes: dict = {}
        self.fleet: dict = {}
        self.forecast: dict = {}
        self.anomalies: dict = {}

    def _load_be(self) -> pd.DataFrame:
        be = pd.read_parquet(settings.FEAT / "bookings_enriched.parquet")
        # Artifacts may carry created_date as date objects or strings; normalize
        # to YYYY-MM-DD so string comparison against data_through works.
        be["created_date"] = pd.to_datetime(be["created_date"]).dt.date.astype(str)
        be["is_real"] = be["is_ghost"].eq(0)
        be["station_fee"] = be["seats"] * settings.STATION_FEE_PER_SEAT
        be["real_rev"] = be["rev"].where(be["is_real"], 0.0)
        return be

    def _data_through(self) -> str:
        s = pd.read_parquet(settings.P3_OUT / "series_total.parquet")
        return str(pd.to_datetime(s["date"]).max().date())

    def load(self) -> None:
        be = self._load_be()
        dt = self._data_through()
        self.data_through = dt
        sub = be[be["created_date"].le(dt)]

        fleet_stats = json.load(open(settings.P2_OUT / "fleet_stats.json"))
        trips = pd.read_parquet(settings.CLEAN / "trips.parquet")
        trips["date"] = pd.to_datetime(trips["start_time"]).dt.date.astype(str)
        trips_day = trips[trips["date"].eq(dt)].groupby("station").size()
        anomaly_summary = json.load(open(settings.P3_OUT / "anomaly_summary.json"))

        stations, anomaly_today = {}, {}
        for st in settings.STATIONS:
            day = be[(be["station"].eq(st)) & (be["created_date"].eq(dt))]
            stations[st] = {
                "bookings_latest_day": int(len(day)),
                "revenue_passenger_paid_latest_day": float(day["rev"].sum()),
                "revenue_station_fee_latest_day": float(day["station_fee"].sum()),
                "real_bookings_latest_day": int(day["is_real"].sum()),
                "ghost_bookings_latest_day": int((~day["is_real"]).sum()),
                "active_vehicles": fleet_stats[st]["vehicles_seen"],
                "trips_latest_day": int(trips_day.get(st, 0)),
            }
            flag = next((x for x in anomaly_summary[st]["flag_days"] if x["date"] == dt), None)
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

        self.overview = {
            "data_through": dt,
            "totals": {
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
            },
            "stations": stations,
            "anomaly_today": anomaly_today,
        }

        hourly = (
            sub.groupby(["station", "hour"], as_index=False)
            .agg(bookings=("id", "count"), seats=("seats", "sum"), revenue_station_fee=("station_fee", "sum"))
            .sort_values(["station", "hour"])
        )
        self.flow_hourly = {"data_through": dt, "series": _recs(hourly)}

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
        self.flow_daily = {"data_through": dt, "series": _recs(daily)}

        rev_daily = (
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
        self.revenue = {
            "data_through": dt,
            "daily": _recs(rev_daily),
            "real_vs_ghost": _recs(rg[["created_date", "real", "ghost"]].rename(columns={"created_date": "date"})),
            "by_route": _recs(by_route.drop(columns=["ghost"])),
        }

        groups = sorted(sub["destination_group"].dropna().unique().tolist())
        self.routes = {"data_through": dt, "groups": groups, "routes": self.revenue["by_route"]}

        trips_cut = trips[trips["date"].le(dt)]
        trips_cut = trips_cut.copy()
        trips_cut["seats_combined"] = trips_cut["seats_booked"].fillna(trips_cut["booked_seats"])
        trips_cut["load_factor"] = trips_cut["seats_combined"] / trips_cut["vehicle_capacity"].replace(0, pd.NA)
        fleet_daily = (
            trips_cut.groupby(["station", "date"], as_index=False)
            .agg(trips=("start_time", "count"), load_factor=("load_factor", "mean"))
            .sort_values(["station", "date"])
        )
        fleet_summary = {}
        for st in settings.STATIONS:
            x = fleet_stats[st]
            fleet_summary[st] = {
                "active_vehicles": x["vehicles_seen"],
                "trips_per_vehicle": x["trips_per_vehicle"],
                "avg_load_factor": x["avg_load_factor"],
                "capacity_coverage_pct": x["load_factor_coverage"],
            }
        self.fleet = {
            "data_through": dt,
            "caveat": "Indicative: Monastir trips carry vehicle capacity on ~33% of rows.",
            "summary": fleet_summary,
            "daily": _recs(fleet_daily),
        }

        self._load_forecast()
        self._load_anomalies()
        self.loaded_at = datetime.now(timezone.utc).isoformat()
        log.info("cache loaded: data_through=%s", dt)

    def _load_forecast(self) -> None:
        metrics = json.load(open(settings.P3_OUT / "model_metrics_v2.json"))
        forecasts, pva = [], []
        for key in settings.KEYS:
            meta = json.load(open(settings.P3_MODELS / f"model_meta_{key}.json"))
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
            if model in ("naive", "seasonal_naive"):
                s = pd.read_parquet(settings.P3_OUT / f"series_{key}.parquet").set_index("date")["bookings"]
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
        self.forecast = {
            "data_through": self.data_through,
            "disclaimer": "Forecast volume includes ghost/draft bookings. "
            "Revenue must be evaluated on real bookings only.",
            "forecasts": forecasts,
            "pred_vs_actual": pva,
        }

    def _load_anomalies(self) -> None:
        d = json.load(open(settings.P3_OUT / "anomaly_summary.json"))
        rows = []
        for key in settings.KEYS:
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
        self.anomalies = {"data_through": self.data_through, "anomalies": rows}

    def reload(self) -> None:
        self.load()
