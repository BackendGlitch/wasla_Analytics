"""Phase 2 - Analysis 3: Route performance (5 destination routes).

Per station x route: volume, passenger-paid revenue, avg ticket, ghost rate,
growth between the busiest month and previous month.

Chart : route_performance.png (volume + revenue facets)
Stats -> output/route_stats.json
"""

import json
import sys
from pathlib import Path
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

sys.path.insert(0, str(Path(__file__).resolve().parent))
from config import FEAT, CHARTS, STATIONS

plt.rcParams.update({"figure.figsize": (12, 6)})
plt.rcParams["savefig.dpi"] = 110


def load() -> pd.DataFrame:
    df = pd.read_parquet(FEAT / "bookings_enriched.parquet")
    df["created_at"] = pd.to_datetime(df["created_at"])
    df["month"] = df["created_at"].dt.to_period("M").astype(str)
    df["is_real"] = df["is_ghost"].eq(0)
    return df


def route_table(be: pd.DataFrame) -> pd.DataFrame:
    g = (
        be.groupby(["station", "destination_canonical"], as_index=False)
        .agg(
            bookings=("id", "count"),
            seats=("seats", "sum"),
            revenue=("rev", "sum"),
            real=("is_real", "sum"),
            ghost=("is_ghost", "sum"),
        )
    )
    g["avg_ticket"] = g["revenue"] / g["bookings"]
    g["ghost_rate"] = g["ghost"] / g["bookings"]
    return g.sort_values(["station", "bookings"], ascending=[True, False])


def monthly_by_route(be: pd.DataFrame) -> pd.DataFrame:
    return (
        be.groupby(["station", "destination_canonical", "month"], as_index=False)
        .agg(bookings=("id", "count"), revenue=("rev", "sum"))
        .sort_values(["station", "destination_canonical", "month"])
    )


def plot_routes(rt: pd.DataFrame) -> Path:
    fig, axes = plt.subplots(1, 2, figsize=(13, 6))
    for ax, metric, title in [
        (axes[0], "bookings", "Route volume (bookings)"),
        (axes[1], "revenue", "Route revenue (TND)"),
    ]:
        top = rt.nlargest(15, metric)
        ax.barh(top["station"] + " -> " + top["destination_canonical"], top[metric])
        ax.invert_yaxis()
        ax.set_title(title)
        ax.set_xlabel(metric)
    fig.tight_layout()
    p = CHARTS / "route_performance.png"
    fig.savefig(p); plt.close(fig)
    return p


def main() -> None:
    be = load()
    rt = route_table(be)
    mr = monthly_by_route(be)

    p = plot_routes(rt)

    stats = {}
    for st in STATIONS:
        sub = be[be["station"] == st]
        busiest_month = sub["month"].value_counts().index[0]
        prev_month = f"{pd.Period(busiest_month, 'M').start_time - pd.DateOffset(months=1):%Y-%m}"
        stats[st] = {
            "busiest_month": busiest_month,
            "total_rt": round(float(rt[rt["station"] == st]["bookings"].sum())),
        }
        # growth per route: month-before vs busiest month
        for _, r in rt[rt["station"] == st].iterrows():
            dest = r["destination_canonical"]
            row = mr[(mr["station"] == st) & (mr["destination_canonical"] == dest)]
            row = row.set_index("month")
            cur = float(row.loc[busiest_month, "bookings"]) if busiest_month in row.index else 0.0
            prev = float(row.loc[prev_month, "bookings"]) if prev_month in row.index else 0.0
            growth = (cur - prev) / prev if prev > 0 else None
            stats[st][dest] = {
                "bookings": int(r["bookings"]),
                "revenue": float(r["revenue"]),
                "avg_ticket": float(r["avg_ticket"]),
                "ghost_rate": float(r["ghost_rate"]),
                "real": int(r["real"]),
                f"growth_{prev_month}_to_{busiest_month}": growth,
            }

    with open(Path(__file__).resolve().parent / "output" / "route_stats.json", "w") as f:
        json.dump(stats, f, indent=2)

    print(f"  {p.name}")
    print("\nRoute table (top by volume):")
    print(rt[rt["bookings"] > 0].head(12).to_string(index=False))
    print("\nStats -> output/route_stats.json")


if __name__ == "__main__":
    main()
