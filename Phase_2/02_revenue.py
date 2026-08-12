"""Phase 2 - Analysis 2: Revenue analytics (dual definition).

Two revenue definitions (see INTERNSHIP_KNOWLEDGE.md 6.1):
  A. passenger-paid : SUM(total_amount) on bookings  (what passengers paid)
  B. station fee     : seats x STATION_FEE_PER_SEAT on bookings + day passes x price

Charts: revenue trend, revenue by route, real vs ghost revenue split.
Stats  -> output/revenue_stats.json
"""

import json
import sys
from pathlib import Path
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

sys.path.insert(0, str(Path(__file__).resolve().parent))
from config import FEAT, CLEAN, CHARTS, STATIONS, STATION_FEE_PER_SEAT, DAY_PASS_PRICE

plt.rcParams.update({"figure.figsize": (11, 5)})
plt.rcParams["savefig.dpi"] = 110


def load() -> pd.DataFrame:
    df = pd.read_parquet(FEAT / "bookings_enriched.parquet")
    df["created_at"] = pd.to_datetime(df["created_at"])
    df["is_real"] = df["is_ghost"].eq(0)
    df["station_fee"] = df["seats"] * STATION_FEE_PER_SEAT
    df["real_rev"] = df["rev"].where(df["is_real"], 0.0)
    return df


def daily_revenue(be: pd.DataFrame) -> pd.DataFrame:
    return (
        be.groupby(["station", "created_date"], as_index=False)
        .agg(
            passenger_paid=("rev", "sum"),
            station_fee=("station_fee", "sum"),
            real_passenger_paid=("real_rev", "sum"),
        )
        .sort_values(["station", "created_date"])
    )


def route_revenue(be: pd.DataFrame) -> pd.DataFrame:
    g = (
        be.groupby(["station", "destination_canonical"], as_index=False)
        .agg(
            bookings=("id", "count"),
            passenger_paid=("rev", "sum"),
            station_fee=("station_fee", "sum"),
            real_rev=("real_rev", "sum"),
        )
    )
    g["avg_ticket"] = g["passenger_paid"] / g["bookings"]
    return g.sort_values(["station", "passenger_paid"], ascending=[True, False])


def plot_daily(dr: pd.DataFrame) -> Path:
    fig, ax = plt.subplots()
    for st in STATIONS:
        sub = dr[dr["station"] == st]
        ax.plot(pd.to_datetime(sub["created_date"]), sub["passenger_paid"], label=f"{st} (passenger-paid)")
    ax.set_title("Daily revenue (passenger-paid)")
    ax.set_xlabel("Date"); ax.set_ylabel("TND / day")
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
    ax.legend()
    fig.tight_layout()
    p = CHARTS / "revenue_daily.png"
    fig.savefig(p); plt.close(fig)
    return p


def plot_route(rr: pd.DataFrame) -> Path:
    fig, ax = plt.subplots(figsize=(10, 6))
    top = rr.nlargest(15, "passenger_paid")
    ax.barh(top["station"] + " -> " + top["destination_canonical"], top["passenger_paid"])
    ax.invert_yaxis()
    ax.set_title("Revenue by route (passenger-paid TND)")
    ax.set_xlabel("TND")
    fig.tight_layout()
    p = CHARTS / "revenue_by_route.png"
    fig.savefig(p); plt.close(fig)
    return p


def plot_real_vs_ghost(be: pd.DataFrame) -> Path:
    fig, ax = plt.subplots(figsize=(8, 6))
    split = (
        be.groupby(["station", "is_real"])["rev"]
        .sum()
        .unstack()
        .fillna(0)
    )
    split.columns = ["ghost", "real"]
    split.plot(kind="bar", ax=ax, stacked=True)
    ax.set_title("Passenger-paid revenue: real vs ghost bookings")
    ax.set_ylabel("TND")
    ax.set_xticklabels([s.capitalize() for s in split.index], rotation=0)
    fig.tight_layout()
    p = CHARTS / "revenue_real_vs_ghost.png"
    fig.savefig(p); plt.close(fig)
    return p


def main() -> None:
    be = load()
    dr = daily_revenue(be)
    rr = route_revenue(be)

    charts = [plot_daily(dr), plot_route(rr), plot_real_vs_ghost(be)]

    stats = {}
    for st in STATIONS:
        sub = be[be["station"] == st]
        dp = pd.read_parquet(CLEAN / "day_passes.parquet")
        dp_st = dp[dp["station"] == st] if "station" in dp.columns else dp
        stats[st] = {
            "passenger_paid_total": float(sub["rev"].sum()),
            "station_fee_bookings": float(sub["station_fee"].sum()),
            "station_fee_day_passes": int(dp_st["price"].sum()) if len(dp_st) else 0,
            "real_bookings_rev": float(sub.loc[sub["is_real"], "rev"].sum()),
            "ghost_bookings_rev": float(sub.loc[~sub["is_real"], "rev"].sum()),
            "avg_ticket_overall": float(sub["rev"].mean()),
            "avg_ticket_real": float(sub.loc[sub["is_real"], "rev"].mean()),
        }

    # consolidated
    stats["consolidated"] = {
        "passenger_paid_total": float(be["rev"].sum()),
        "station_fee_total": float(be["station_fee"].sum()),
        "real_rev_total": float(be.loc[be["is_real"], "rev"].sum()),
        "ghost_rev_total": float(be.loc[~be["is_real"], "rev"].sum()),
    }

    with open(Path(__file__).resolve().parent / "output" / "revenue_stats.json", "w") as f:
        json.dump(stats, f, indent=2)

    print("Charts:")
    for p in charts:
        print(f"  {p.name}")
    print("\nStats -> output/revenue_stats.json")


if __name__ == "__main__":
    main()
