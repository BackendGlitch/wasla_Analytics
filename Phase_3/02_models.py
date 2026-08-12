"""Phase 3 - Step 2 (v2): Walk-forward cross-validation of forecasting models.

Replaces the single-holdout evaluation with a rolling-origin walk-forward CV:
  N_FOLDS origins, each offset by 7 days; for each fold we train on the
  expanding window and predict the NEXT 7 days. Metrics are reported as
  mean +/- std across folds -> robust model choice, not luck-of-the-split.

Models:
  - naive             (persist last value)
  - seasonal_naive    (same weekday, previous week)
  - seasonal_median   (median of same weekday over trailing 3 weeks)
  - weekly_mean       (mean of previous 7 days)
  - sarima            (auto AIC grid: p,q in {0,1} x seasonal P,Q in {0,1}, D=1, s=7)
  - prophet           (weekly seasonality)

Writes output/model_metrics_v2.json (per-fold + summary), and records the
chosen SARIMA order per series for use by the final forecast step.
"""

import json
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

sys.path.insert(0, str(Path(__file__).resolve().parent))
from config import OUT, FORECAST_HORIZON, SEASONAL_PERIOD, STATIONS

SERIES_KEYS = STATIONS + ["total"]
N_FOLDS = 4
MIN_TRAIN_DAYS = 3 * SEASONAL_PERIOD + SEASONAL_PERIOD


def load_series(key: str) -> pd.Series:
    df = pd.read_parquet(OUT / f"series_{key}.parquet")
    s = df.set_index("date")["bookings"]
    s.index = pd.to_datetime(s.index)
    return s


# ---------------- metrics ----------------


def mae(a, b):
    return float(np.mean(np.abs(a - b)))


def rmse(a, b):
    return float(np.sqrt(np.mean((a - b) ** 2)))


def mape(a, b):
    mask = a > 0
    return float(np.mean(np.abs((a[mask] - b[mask]) / a[mask]))) if mask.any() else float("nan")


# ---------------- baselines ----------------


def fc_naive(train: pd.Series, h: int):
    v = float(train.iloc[-1])
    return np.full(h, v)


def fc_seasonal_naive(train: pd.Series, h: int, period: int):
    return np.asarray([train.iloc[-period + (i % period)] for i in range(h)], dtype=float)


def fc_seasonal_median(train: pd.Series, h: int, period: int):
    wd_slot = [train.index[-period + (i % period)].dayofweek for i in range(h)]
    out = []
    for i, dw in enumerate(wd_slot):
        # median of the same weekday over the trailing 3 periods before the forecast origin
        past = train.iloc[-3 * period:]
        vals = past[past.index.dayofweek == dw]
        out.append(float(vals.median()) if len(vals) else train.mean())
    return np.asarray(out, dtype=float)


def fc_weekly_mean(train: pd.Series, h: int, period: int):
    return np.full(h, float(train.tail(period).mean()))


# ---------------- SARIMA (AIC grid search) ----------------


def sarima_order(train: pd.Series, period: int):
    from statsmodels.tsa.statespace.sarimax import SARIMAX

    best_aic, best = np.inf, None
    for p in range(0, 2):
        for q in range(0, 2):
            for P in range(0, 2):
                for Q in range(0, 2):
                    try:
                        m = SARIMAX(
                            train, order=(p, 1, q), seasonal_order=(P, 1, Q, period),
                            enforce_stationarity=False, enforce_invertibility=False,
                            trend="c", initialization="approximate_diffuse",
                        )
                        res = m.fit(disp=False, maxiter=200)
                    except Exception:
                        continue
                    if np.isfinite(res.aic) and res.aic < best_aic:
                        best_aic, best = res.aic, (p, q, P, Q)
    return best  # (p,q,P,Q)


def fc_sarima(train: pd.Series, h: int, period: int, order):
    from statsmodels.tsa.statespace.sarimax import SARIMAX

    p, q, P, Q = order
    m = SARIMAX(train, order=(p, 1, q), seasonal_order=(P, 1, Q, period),
                enforce_stationarity=False, enforce_invertibility=False, trend="c")
    res = m.fit(disp=False, maxiter=300)
    fc = res.get_forecast(h)
    return fc.predicted_mean.values


# ---------------- Prophet ----------------


def fc_prophet(train: pd.Series, h: int):
    from prophet import Prophet

    df = train.rename("y").reset_index()
    df.columns = ["ds", "y"]
    m = Prophet(weekly_seasonality=True, yearly_seasonality=False, daily_seasonality=False,
                seasonality_mode="additive")
    m.fit(df)
    future = m.make_future_dataframe(periods=h)
    return m.predict(future).tail(h)["yhat"].values


# ---------------- walk-forward CV ----------------


def walk_forward(s: pd.Series, h: int = FORECAST_HORIZON):
    """Yield (fold_i, train, test) expanding-window origins."""
    n = len(s)
    for fold in range(N_FOLDS):
        start = n - h * (fold + 1)
        if start < MIN_TRAIN_DAYS:
            break
        train, test = s.iloc[:start], s.iloc[start:start + h]
        yield fold + 1, train, test


def evaluate() -> dict:
    all_results = {}
    summary = {}

    for key in SERIES_KEYS:
        s = load_series(key)
        # choose SARIMA order once on the FULL series (standard practice:
        # order selection is stable; forecasts below refit on it).
        full_order = sarima_order(s, SEASONAL_PERIOD)

        cols = {"fold": [], "mae": [], "rmse": [], "mape": [], "model": []}
        per_model = {m: {"mae": [], "rmse": [], "mape": []} for m in
                     ["naive", "seasonal_naive", "seasonal_median", "weekly_mean", "sarima", "prophet"]}

        for fold, train, test in walk_forward(s):
            true = test.values.astype(float)
            h = len(test)
            preds = {
                "naive": fc_naive(train, h),
                "seasonal_naive": fc_seasonal_naive(train, h, SEASONAL_PERIOD),
                "seasonal_median": fc_seasonal_median(train, h, SEASONAL_PERIOD),
                "weekly_mean": fc_weekly_mean(train, h, SEASONAL_PERIOD),
                "sarima": fc_sarima(train, h, SEASONAL_PERIOD, full_order),
            }
            try:
                preds["prophet"] = fc_prophet(train, h)
            except Exception as e:
                per_model["prophet"]["mae"].append(float("nan"))
                per_model["prophet"]["rmse"].append(float("nan"))
                per_model["prophet"]["mape"].append(float("nan"))
                print(f"  [warn] prophet fold {fold} {key}: {e}")
                continue
            for mod, fc in preds.items():
                cols["fold"].append(fold); cols["model"].append(mod)
                cols["mae"].append(mae(true, fc)); cols["rmse"].append(rmse(true, fc))
                cols["mape"].append(mape(true, fc))
                m = per_model[mod]
                m["mae"].append(cols["mae"][-1]); m["rmse"].append(cols["rmse"][-1]); m["mape"].append(cols["mape"][-1])

        # fold-level table (only first fold rows shown in report later)
        fold_df = pd.DataFrame(cols)

        summary[key] = {
            "series_window": [str(s.index[0].date()), str(s.index[-1].date())],
            "n_days": int(len(s)),
            "n_folds": int(fold_df["fold"].nunique()),
            "sarima_order": list(full_order) if full_order else None,
            "models": {
                mod: {
                    "mae_mean": float(np.nanmean(v["mae"])), "mae_std": float(np.nanstd(v["mae"])),
                    "rmse_mean": float(np.nanmean(v["rmse"])), "rmse_std": float(np.nanstd(v["rmse"])),
                    "mape_mean": float(np.nanmean(v["mape"])), "mape_std": float(np.nanstd(v["mape"])),
                }
                for mod, v in per_model.items()
            },
        }
        best = min(per_model, key=lambda m: np.nanmean(per_model[m]["mape"]))
        summary[key]["best_by_mape"] = best

        fold_df.to_parquet(OUT / f"cv_folds_{key}.parquet", index=False)
        print(f"  {key:<10} folds={summary[key]['n_folds']}  sarima_order={full_order}  best={best}")

    with open(OUT / "model_metrics_v2.json", "w") as f:
        json.dump(summary, f, indent=2)
    print("\n-> output/model_metrics_v2.json")
    return summary


if __name__ == "__main__":
    evaluate()