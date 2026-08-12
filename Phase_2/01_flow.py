"""Phase 2 - Analysis 1: Passenger flow & peak hours.

Outputs charts + a JSON stats snippet to output/flow_stats.json.

Passenger flow = bookings over time. Ghost bookings are included for VOLUME
(whenever a ticket is generated the flow exists), but we also report the
'real' subset separately because ghosts dominate (see config.GHOST_NOTE).
"""

import json
from pathlib import Path
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
from config import FEAT, CHARTS, STATIONS, GHOST_NOTE

plt.rcParams.update({"figure.figsize": (11, 5)})
plt.rcParams["savefig.dpi"] = 110


def load_enriched() -> pd.DataFrame:
    df = pd.read_parquet(FEAT / "bookings_enriched.parquet")
    df["created_at"] = pd.to_datetime(df["created_at"])
    df["is_real"] = df["is_ghost"].eq(0)
    return df


def hourly_curve(be: pd.DataFrame) -> pd.DataFrame:
    return (
        be.groupby(["station", "hour"], as_index=False)
        .agg(bookings=("id", "count"))
        .sort_values(["station", "hour"])
    )


def daily_series(be: pd.DataFrame) -> pd.DataFrame:
    return (
        be.groupby(["station", "created_date"], as_index=False)
        .agg(bookings=("id", "count"), real=("is_real", "sum"))
        .sort_values(["station", "created_date"])
    )


def weekday_profile(be: pd.DataFrame) -> pd.DataFrame:
    return (
        be.groupby(["station", "weekday"], as_index=False)
        .agg(bookings=("id", "count"))
        .sort_values(["station", "weekday"])
    )


def plot_hourly(curve: pd.DataFrame) -> Path:
    fig, ax = plt.subplots()
    for st in STATIONS:
        sub = curve[curve["station"] == st]
        ax.plot(sub["hour"], sub["bookings"], marker="o", label=st.capitalize())
    ax.set_title("Passenger flow by hour of day (total bookings)")
    ax.set_xlabel("Hour")
    ax.set_ylabel("Total bookings")
    ax.legend()
    fig.tight_layout()
    p = CHARTS / "flow_hourly.png"
    fig.savefig(p); plt.close(fig)
    return p


def plot_daily(daily: pd.DataFrame) -> Path:
    fig, ax = plt.subplots()
    for st in STATIONS:
        sub = daily[daily["station"] == st]
        ax.plot(pd.to_datetime(sub["created_date"]), sub["bookings"], label=st.capitalize())
    ax.set_title("Daily passenger flow")
    ax.set_xlabel("Date")
    ax.set_ylabel("Bookings / day")
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
    ax.legend()
    fig.tight_layout()
    p = CHARTS / "flow_daily.png"
    fig.savefig(p); plt.close(fig)
    return p


def plot_weekday(wd: pd.DataFrame) -> Path:
    fig, ax = plt.subplots()
    labels = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    width = 0.38
    for i, st in enumerate(STATIONS):
        sub = wd[wd["station"] == st].set_index("weekday")["bookings"]
        sub = sub.reindex(range(7)).fillna(0)
        # group bars side-by-side within each weekday bucket
        x = [j - width / 2 + i * width for j in range(7)]
        ax.bar(x, sub.values, width, label=st.capitalize())
    ax.set_xticks(range(7)); ax.set_xticklabels(labels)
    ax.set_title("Bookings by day of week")
    ax.set_ylabel("Total bookings")
    ax.legend()
    fig.tight_layout()
    p = CHARTS / "flow_weekday.png"
    fig.savefig(p); plt.close(fig)
    return p


def main() -> None:
    be = load_enriched()
    hourly = hourly_curve(be)
    daily = daily_series(be)
    weekday = weekday_profile(be)

    charts = [plot_hourly(hourly), plot_daily(daily), plot_weekday(weekday)]

    # ---- derived stats ----
    stats = {"ghost_note": GHOST_NOTE}
    for st in STATIONS:
        sub = be[be["station"] == st]
        d = sub.groupby("created_date")["id"].count()
        stats[st] = {
            "total_bookings": int(len(sub)),
            "real_bookings": int(sub["is_real"].sum()),
            "ghost_rate": float(sub["is_ghost"].mean()),
            "avg_bookings_per_day": float(d.mean()),
            "peak_hour": int(hourly[hourly["station"] == st].set_index("hour")["bookings"].idxmax()),
            "peak_offpeak_ratio": None,
        }
        # peak-to-off-peak: peak hour vs median hour
        h = hourly[hourly["station"] == st].set_index("hour")["bookings"]
        stats[st]["peak_offpeak_ratio"] = float(h.max() / h.median())

    (OUT := Path(__file__).resolve().parent / "output").mkdir(exist_ok=True)
    with open(OUT / "flow_stats.json", "w") as f:
        json.dump(stats, f, indent=2)

    print("Charts:")
    for p in charts:
        print(f"  {p.name}")
    print("\nStats -> output/flow_stats.json")


if __name__ == "__main__":
    main()
