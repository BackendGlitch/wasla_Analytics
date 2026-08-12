"""Phase 1 - Step 3: Feature engineering / derived aggregates.

Builds analytical datasets on top of the clean layer:
  data/features/
    bookings_enriched.parquet   bookings + calendar/time features + derived flags
    demand_hourly.parquet       bookings, seats, revenue by hour-of-day x station
    demand_daily.parquet        bookings, seats, revenue, ghost% by date x station x destination
    route_performance.parquet   per-destination success/cancellation/pricing stats

Run:  python3 03_features.py
"""

import sys
from pathlib import Path
import pandas as pd

BASE = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE))
from config import destination_lookup

CLEAN = BASE / "data" / "clean"
FEAT = BASE / "data" / "features"
FEAT.mkdir(parents=True, exist_ok=True)


def load_clean(table: str) -> pd.DataFrame:
    return pd.read_parquet(CLEAN / f"{table}.parquet")


def enrich_bookings() -> pd.DataFrame:
    df = load_clean("bookings")
    ts = df["created_at"]
    df["hour"] = ts.dt.hour
    df["weekday"] = ts.dt.dayofweek
    df["month"] = ts.dt.month
    df["year"] = ts.dt.year
    df["is_weekend"] = df["weekday"] >= 5
    df["hour_bucket"] = pd.cut(
        df["hour"],
        bins=[-1, 6, 10, 14, 18, 22, 24],
        labels=["night(0-6)", "morning(6-10)", "midday(10-14)", "afternoon(14-18)", "evening(18-22)", "late(22-24)"],
    )
    df["is_cancelled"] = df["booking_status"].eq("CANCELLED").astype(int)
    df["is_ghost"] = df["is_ghost_booking"].fillna(False).astype(int)
    df["rev"] = df["total_amount"].fillna(0.0)
    df["seats"] = df["seats_booked"].fillna(1).astype(int)

    # Unified destination names across stations (st_* vs station-*).
    dest = df["destination_id"].apply(
        lambda x: destination_lookup(x) if pd.notna(x) else {"canonical": "Unknown", "group": "Unknown"}
    )
    df["destination_canonical"] = dest.apply(lambda m: m["canonical"])
    df["destination_group"] = dest.apply(lambda m: m["group"])
    return df


def demand_hourly(be: pd.DataFrame) -> pd.DataFrame:
    g = (
        be.groupby(["station", "hour"], as_index=False)
        .agg(bookings=("id", "count"), seats=("seats", "sum"), revenue=("rev", "sum"))
    )
    return g.sort_values(["station", "hour"])


def demand_daily(be: pd.DataFrame) -> pd.DataFrame:
    g = (
        be.groupby(["station", "created_date", "destination_canonical"], as_index=False)
        .agg(
            bookings=("id", "count"),
            seats=("seats", "sum"),
            revenue=("rev", "sum"),
            cancelled=("is_cancelled", "sum"),
            ghost=("is_ghost", "sum"),
        )
    )
    g["cancel_rate"] = g["cancelled"] / g["bookings"]
    g["ghost_rate"] = g["ghost"] / g["bookings"]
    return g.sort_values(["station", "created_date", "destination_canonical"])


def route_performance(be: pd.DataFrame) -> pd.DataFrame:
    g = (
        be.groupby(["station", "destination_canonical"], as_index=False)
        .agg(
            destination_group=("destination_group", "first"),
            total_bookings=("id", "count"),
            avg_seats=("seats", "mean"),
            avg_rev=("rev", "mean"),
            median_rev=("rev", "median"),
            cancelled=("is_cancelled", "sum"),
            ghost=("is_ghost", "sum"),
            distinct_days=("created_date", "nunique"),
        )
    )
    g["cancel_rate"] = g["cancelled"] / g["total_bookings"]
    g["ghost_rate"] = g["ghost"] / g["total_bookings"]
    return g.sort_values(["station", "total_bookings"], ascending=[True, False])


def main() -> None:
    print("Building bookings_enriched ...")
    be = enrich_bookings()
    be.to_parquet(FEAT / "bookings_enriched.parquet", index=False)
    print(f"  -> {len(be):,} rows")

    print("Building demand_hourly ...")
    dh = demand_hourly(be)
    dh.to_parquet(FEAT / "demand_hourly.parquet", index=False)
    print(f"  -> {len(dh):,} rows")

    print("Building demand_daily ...")
    dd = demand_daily(be)
    dd.to_parquet(FEAT / "demand_daily.parquet", index=False)
    print(f"  -> {len(dd):,} rows")

    print("Building route_performance ...")
    rp = route_performance(be)
    rp.to_parquet(FEAT / "route_performance.parquet", index=False)
    print(f"  -> {len(rp):,} rows")

    print("\n=== FEATURE FILES ===")
    for f in sorted(FEAT.glob("*.parquet")):
        print(f"  {f.name:<32} {f.stat().st_size/1e6:,.2f} MB")


if __name__ == "__main__":
    main()
