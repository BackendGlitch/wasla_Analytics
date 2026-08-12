"""Phase 3 - Step 4 (v3): Anomaly detection on daily booking volume.

Three complementary detectors:
  1. rolling_z         classic rolling z-score (level-based)
  2. wow_z             week-over-week differencing: z-score of (y_t - y_{t-7})
                       against a rolling distribution -> removes weekly pattern
  3. isolation_forest  sklearn on lag/rolling features

consensus = >=2 of the 3 detectors flag the day (avoids single-detector noise).

Outputs: output/anomalies_{key}.parquet + charts/anomalies_{key}.png
"""

import json
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from sklearn.ensemble import IsolationForest

warnings.filterwarnings("ignore")

sys.path.insert(0, str(Path(__file__).resolve().parent))
from config import OUT, CHARTS, STATIONS, SEASONAL_PERIOD

plt.rcParams.update({"figure.figsize": (13, 6)})
plt.rcParams["savefig.dpi"] = 110


def load_series(key: str) -> pd.Series:
    df = pd.read_parquet(OUT / f"series_{key}.parquet")
    s = df.set_index("date")["bookings"]
    s.index = pd.to_datetime(s.index)
    return s


def rolling_zflag(s: pd.Series, window: int = 14, thresh: float = 3.0) -> pd.Series:
    mean = s.rolling(window, min_periods=5).mean()
    std = s.rolling(window, min_periods=5).std()
    z = (s - mean) / std.replace(0, np.nan)
    return (z.abs() > thresh).fillna(False)


def wow_zflag(s: pd.Series, window: int = 28, thresh: float = 3.0) -> pd.Series:
    """Flag days whose week-over-week change is an outlier.

    residual_t = y_t - y_{t-7}; standardised against a rolling 28-day
    distribution of residuals -> adjusts for the weekly pattern.
    """
    diff = s.diff(SEASONAL_PERIOD)
    roll_mean = diff.rolling(window, min_periods=10).mean()
    roll_std = diff.rolling(window, min_periods=10).std()
    z = (diff - roll_mean) / roll_std.replace(0, np.nan)
    return (z.abs() > thresh).fillna(False)


def isoflag(s: pd.Series) -> pd.Series:
    df = pd.DataFrame({"y": s.values})
    df["lag1"] = df["y"].shift(1)
    df["lag7"] = df["y"].shift(7)
    df["roll_mean"] = df["y"].rolling(7).mean()
    df["roll_std"] = df["y"].rolling(7).std()
    df["weekday"] = s.index.dayofweek
    feat = df[["lag1", "lag7", "roll_mean", "roll_std", "weekday"]].ffill().bfill().fillna(0)
    iso = IsolationForest(contamination=0.02, random_state=42, n_jobs=-1)
    pred = iso.fit_predict(feat)
    return pd.Series(pred == -1, index=s.index)


def main() -> None:
    summary = {}
    for key in STATIONS + ["total"]:
        s = load_series(key)
        rz = rolling_zflag(s)
        wz = wow_zflag(s)
        iso = isoflag(s)
        # 0-booking day on an otherwise busy series is operationally anomalous;
        # rolling z can miss it (high variance window) so add it explicitly.
        trailing_mean = s.rolling(7).mean().shift(1)
        zero_day = (s == 0) & (trailing_mean > 100)
        votes = (rz.values.astype(int) + wz.values.astype(int) + iso.values.astype(int))
        consensus = pd.Series((votes >= 2) | zero_day.values, index=s.index)

        df = pd.DataFrame(
            {"bookings": s.values, "rolling_z": rz.values, "wow_z": wz.values,
             "isolation_forest": iso.values, "consensus": consensus.values},
            index=s.index,
        )
        df.to_parquet(OUT / f"anomalies_{key}.parquet")

        flag_days = df.index[consensus]
        summary[key] = {
            "rolling_z": int(rz.sum()), "wow_z": int(wz.sum()),
            "isolation_forest": int(iso.sum()),             "consensus": int(consensus.sum()),
            "flag_days": [
                {"date": str(d.date()), "bookings": int(df.loc[d, "bookings"]),
                 "wow_z": bool(wz[d]), "rolling_z": bool(rz[d]), "iso": bool(iso[d]),
                 "zero_day": bool(zero_day[d])}
                for d in flag_days
            ],
        }
        print(f"  {key:<10} rolling_z={rz.sum()} wow_z={wz.sum()} iso={iso.sum()} consensus={consensus.sum()}")

        fig, ax = plt.subplots()
        ax.plot(s.index, s.values, color="tab:blue", label="daily bookings")
        ax.fill_between(s.index, 0, s.values, where=consensus, step="mid",
                        color="tab:red", alpha=0.35, label="consensus anomaly")
        ax.scatter(s.index[rz], s.loc[rz], color="tab:orange", s=30, zorder=5, label="rolling z")
        ax.scatter(s.index[iso], s.loc[iso], marker="x", color="tab:green", s=60, zorder=6, label="isolation forest")
        ax.scatter(s.index[wz], s.loc[wz], marker="^", color="tab:purple", s=50, zorder=5, label="WoW-diff z")
        ax.set_title(f"{key.capitalize()} — daily volume anomalies (consensus={summary[key]['consensus']})")
        ax.set_xlabel("Date"); ax.set_ylabel("Bookings")
        ax.legend()
        fig.tight_layout()
        fig.savefig(CHARTS / f"anomalies_{key}.png"); plt.close(fig)

    with open(OUT / "anomaly_summary.json", "w") as f:
        json.dump(summary, f, indent=2)
    print("\n-> output/anomalies_{key}.parquet + charts/anomalies_{key}.png")


if __name__ == "__main__":
    main()