"""Phase 2 - Analysis 4: Fleet utilization + cancellation analysis.

Fleet: trips per vehicle, load factor (seats_booked / vehicle_capacity),
active vehicles per day, share of trips per destination.
Cancellations: rate, reasons, by-destination distribution.

Charts: fleet_utilization.png, cancellations.png
Stats -> output/fleet_stats.json, output/cancellation_stats.json
"""

import json
import sys
from pathlib import Path
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

sys.path.insert(0, str(Path(__file__).resolve().parent))
from config import CLEAN, FEAT, CHARTS, STATIONS

plt.rcParams.update({"figure.figsize": (11, 5)})
plt.rcParams["savefig.dpi"] = 110


def load_trips() -> pd.DataFrame:
    t = pd.read_parquet(CLEAN / "trips.parquet")
    t["start_time"] = pd.to_datetime(t["start_time"])
    # Station schemas differ: Jemmal fills `booked_seats`, Monastir fills
    # `seats_booked`. Combine into a single column before computing load.
    t["seats_combined"] = t["seats_booked"].fillna(t["booked_seats"])
    t["load_factor"] = t["seats_combined"] / t["vehicle_capacity"].replace(0, pd.NA)
    return t


def load_cancellations() -> pd.DataFrame:
    be = pd.read_parquet(FEAT / "bookings_enriched.parquet")
    be["is_cancelled"] = be["booking_status"].eq("CANCELLED")
    return be


def plot_fleet(t: pd.DataFrame) -> Path:
    fig, axes = plt.subplots(1, 2, figsize=(13, 5))

    lf = t.dropna(subset=["load_factor"])
    for ax, st in zip(axes, STATIONS):
        sub = lf[lf["station"] == st]
        ax.hist(sub["load_factor"].clip(0, 1), bins=20, alpha=0.7, label=st.capitalize())
        ax.axvline(sub["load_factor"].mean(), color="tab:red", ls="--", label=f"mean {sub['load_factor'].mean():.2f}")
        ax.set_title(f"Load factor distribution — {st.capitalize()} (n={len(sub)})")
        ax.set_xlabel("Load factor (booked/capacity)")
        ax.legend()

    fig.tight_layout()
    p = CHARTS / "fleet_load_factor.png"
    fig.savefig(p); plt.close(fig)
    return p


def plot_cancellations(be: pd.DataFrame) -> Path:
    fig, ax = plt.subplots()
    sub = be[be["is_cancelled"]]
    if len(sub):
        by_route = sub.groupby(["station", "destination_canonical"]).size().nlargest(15)
        ax.barh([f"{a}->{b}" for a, b in by_route.index], by_route.values)
        ax.set_title("Cancellations by route")
    else:
        ax.text(0.5, 0.5, "No cancellations found", ha="center")
    ax.set_xlabel("Count")
    fig.tight_layout()
    p = CHARTS / "cancellations.png"
    fig.savefig(p); plt.close(fig)
    return p


def main() -> None:
    t = load_trips()
    be = load_cancellations()

    charts = [plot_fleet(t), plot_cancellations(be)]

    fleet = {}
    for st in STATIONS:
        sub = t[t["station"] == st]
        lf_valid = sub["load_factor"].dropna()
        fleet[st] = {
            "trips": int(len(sub)),
            "vehicles_seen": int(sub["vehicle_id"].nunique()),
            "trips_per_vehicle": float(sub.groupby("vehicle_id").size().mean()),
            "avg_load_factor": float(lf_valid.mean()) if len(lf_valid) else None,
            "load_factor_coverage": float(len(lf_valid) / len(sub)) if len(sub) else None,
            "date_from": str(sub["start_time"].min()),
            "date_to": str(sub["start_time"].max()),
        }

    cancellations = {}
    for st in STATIONS:
        sub = be[be["station"] == st]
        cancelled = sub[sub["is_cancelled"]]
        cancellations[st] = {
            "total": int(len(sub)),
            "cancelled": int(len(cancelled)),
            "cancel_rate": float(cancelled.shape[0] / len(sub) if len(sub) else 0),
            "reasons": cancelled["cancellation_reason"].value_counts().head(5).to_dict(),
        }

    with open(Path(__file__).resolve().parent / "output" / "fleet_stats.json", "w") as f:
        json.dump(fleet, f, indent=2)
    with open(Path(__file__).resolve().parent / "output" / "cancellation_stats.json", "w") as f:
        json.dump(cancellations, f, indent=2)

    print("Charts:")
    for p in charts:
        print(f"  {p.name}")
    print("\nFleet stats:")
    print(pd.DataFrame(fleet).T.to_string())
    print("\nCancellation stats:")
    print(pd.DataFrame(cancellations).T.to_string())


if __name__ == "__main__":
    main()
