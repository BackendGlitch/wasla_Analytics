"""Phase 1 - Step 4: Exploratory Data Analysis.

Produces charts and a summary report to data/eda/ from the feature layer.

Run:  python3 04_eda.py
"""

from pathlib import Path
import pandas as pd
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

BASE = Path(__file__).resolve().parent
FEAT = BASE / "data" / "features"
EDA = BASE / "data" / "eda"
EDA.mkdir(parents=True, exist_ok=True)

plt.rcParams.update({"figure.figsize": (10, 5)})
plt.rcParams["savefig.dpi"] = 110


def load(table: str) -> pd.DataFrame:
    return pd.read_parquet(FEAT / f"{table}.parquet")


def plot_demand_hourly(dh: pd.DataFrame) -> Path:
    fig, ax = plt.subplots()
    for st in ["jemmal", "monastir"]:
        sub = dh[dh["station"] == st]
        ax.plot(sub["hour"], sub["bookings"], marker="o", label=st)
    ax.set_title("Bookings by hour of day")
    ax.set_xlabel("Hour")
    ax.set_ylabel("Total bookings")
    ax.legend()
    fig.tight_layout()
    p = EDA / "demand_by_hour.png"
    fig.savefig(p)
    plt.close(fig)
    return p


def plot_demand_daily(dd: pd.DataFrame) -> Path:
    daily = dd.groupby(["station", "created_date"], as_index=False)["bookings"].sum()
    fig, ax = plt.subplots()
    for st in ["jemmal", "monastir"]:
        sub = daily[daily["station"] == st]
        ax.plot(pd.to_datetime(sub["created_date"]), sub["bookings"], label=st)
    ax.set_title("Daily bookings")
    ax.set_xlabel("Date")
    ax.set_ylabel("Bookings")
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
    ax.legend()
    fig.tight_layout()
    p = EDA / "demand_by_day.png"
    fig.savefig(p)
    plt.close(fig)
    return p


def plot_route_bar(rp: pd.DataFrame) -> Path:
    fig, ax = plt.subplots(figsize=(10, 6))
    top = rp.nlargest(15, "total_bookings")
    ax.barh(
        top["station"] + " -> " + top["destination_canonical"],
        top["total_bookings"],
    )
    ax.set_title("Top routes by bookings")
    ax.invert_yaxis()
    ax.set_xlabel("Total bookings")
    fig.tight_layout()
    p = EDA / "top_routes.png"
    fig.savefig(p)
    plt.close(fig)
    return p


def plot_status_pie(be: pd.DataFrame) -> Path:
    fig, ax = plt.subplots(figsize=(6, 6))
    counts = be["booking_status"].value_counts()
    ax.pie(counts, labels=counts.index, autopct="%.1f%%")
    ax.set_title("Booking status distribution")
    fig.tight_layout()
    p = EDA / "status_pie.png"
    fig.savefig(p)
    plt.close(fig)
    return p


def main() -> None:
    be = load("bookings_enriched")
    dh = load("demand_hourly")
    dd = load("demand_daily")
    rp = load("route_performance")

    charts = [
        plot_demand_hourly(dh),
        plot_demand_daily(dd),
        plot_route_bar(rp),
        plot_status_pie(be),
    ]

    lines = []
    lines.append("# Phase 1 EDA Summary")
    lines.append("")
    lines.append(f"- Generated: {pd.Timestamp.now():%Y-%m-%d %H:%M}")
    lines.append("")
    lines.append("## Data volumes")
    lines.append("")
    lines.append(f"- Total bookings: **{len(be):,}**")
    lines.append(f"- By station: " + ", ".join(f"{k}={v:,}" for k, v in be["station"].value_counts().to_dict().items()))
    lines.append(f"- Date range: {be['created_at'].min()} -> {be['created_at'].max()}")
    lines.append("")
    lines.append("## Booking status")
    lines.append("")
    for k, v in be["booking_status"].value_counts().items():
        lines.append(f"- {k}: {v:,} ({v / len(be):.2%})")
    lines.append("")
    lines.append("## Ghost bookings")
    lines.append("")
    lines.append(f"- Ghost: {be['is_ghost'].sum():,} ({be['is_ghost'].mean():.2%})")
    lines.append("")
    lines.append("## Hourly demand (peak hours)")
    lines.append("")
    for st in ["jemmal", "monastir"]:
        top = dh[dh["station"] == st].nlargest(3, "bookings")
        peak = ", ".join(f"{int(r.hour)}h ({r.bookings:,})" for _, r in top.iterrows())
        lines.append(f"- {st}: {peak}")
    lines.append("")
    lines.append("## Revenue")
    lines.append("")
    lines.append(f"- Total revenue (bookings): **{be['rev'].sum():,.0f} TND**")
    lines.append(f"- Avg revenue/booking: {be['rev'].mean():,.2f} TND")
    lines.append("")
    lines.append("## Route performance")
    lines.append("")
    for st in ["jemmal", "monastir"]:
        sub = rp[rp["station"] == st].nlargest(5, "total_bookings")
        for _, r in sub.iterrows():
            lines.append(
                f"- {st} -> {r['destination_canonical']}: {r['total_bookings']:,} bookings, "
                f"avg {r['avg_rev']:.2f} TND"
            )
    lines.append("")
    lines.append("## Charts")
    lines.append("")
    for p in charts:
        lines.append(f"![{p.stem}]({p.name})")

    (EDA / "SUMMARY.md").write_text("\n".join(lines))
    print(f"Charts + summary written to {EDA}")
    for p in charts:
        print(f"  {p.name}")


if __name__ == "__main__":
    main()
