"""Phase 3 - Step 3 (v2): 7-day forward forecast using CV-selected model.

Uses the best model per series from model_metrics_v2.json. For SARIMA,
refits with the SAME order chosen at CV time (eval/forecast consistency).
Persists model metadata + interval to models/ for the Phase 4 dashboard.

Outputs: output/forecast_{key}.parquet, charts/forecast_{key}.png,
         models/model_meta_{key}.json
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

warnings.filterwarnings("ignore")

sys.path.insert(0, str(Path(__file__).resolve().parent))
from config import OUT, CHARTS, MODELS, FORECAST_HORIZON, SEASONAL_PERIOD, STATIONS


SERIES_KEYS = STATIONS + ["total"]
plt.rcParams.update({"figure.figsize": (12, 5)})
plt.rcParams["savefig.dpi"] = 110


def load_series(key: str) -> pd.Series:
    df = pd.read_parquet(OUT / f"series_{key}.parquet")
    s = df.set_index("date")["bookings"]
    s.index = pd.to_datetime(s.index)
    return s


def best_model_and_order(key: str):
    m = json.load(open(OUT / "model_metrics_v2.json"))[key]
    return m["best_by_mape"], tuple(m["sarima_order"]) if m["sarima_order"] else None


def fit_predict(s: pd.Series, model: str, order, h: int):
    """Refit on FULL series and return (mean, lo, hi)."""
    if model == "naive":
        v = float(s.iloc[-1])
        return np.full(h, v), np.full(h, v), np.full(h, v)
    if model == "seasonal_naive":
        out = np.asarray([s.iloc[-SEASONAL_PERIOD + (i % SEASONAL_PERIOD)] for i in range(h)], dtype=float)
        return out, None, None
    if model == "seasonal_median":
        out = []
        for i in range(h):
            dw = s.index[-SEASONAL_PERIOD + (i % SEASONAL_PERIOD)].dayofweek
            vals = s.iloc[-3 * SEASONAL_PERIOD:][s.iloc[-3 * SEASONAL_PERIOD:].index.dayofweek == dw]
            out.append(float(vals.median()) if len(vals) else s.mean())
        return np.asarray(out, dtype=float), None, None
    if model == "weekly_mean":
        v = float(s.tail(SEASONAL_PERIOD).mean())
        return np.full(h, v), None, None
    if model == "sarima":
        from statsmodels.tsa.statespace.sarimax import SARIMAX
        p, q, P, Q = order
        m = SARIMAX(s, order=(p, 1, q), seasonal_order=(P, 1, Q, SEASONAL_PERIOD),
                    enforce_stationarity=False, enforce_invertibility=False, trend="c")
        res = m.fit(disp=False, maxiter=400)
        fc = res.get_forecast(h)
        ci = fc.conf_int()
        return fc.predicted_mean.values, ci.iloc[:, 0].values, ci.iloc[:, 1].values
    if model == "prophet":
        from prophet import Prophet
        df = s.rename("y").reset_index()
        df.columns = ["ds", "y"]
        m = Prophet(weekly_seasonality=True, yearly_seasonality=False, daily_seasonality=False)
        m.fit(df)
        future = m.make_future_dataframe(periods=h)
        p = m.predict(future).tail(h)
        return p["yhat"].values, p["yhat_lower"].values, p["yhat_upper"].values
    raise ValueError(model)


def main() -> None:
    forecast_out = {}
    dates_out = {}
    for key in SERIES_KEYS:
        s = load_series(key)
        model, order = best_model_and_order(key)
        mean, lo, hi = fit_predict(s, model, order, FORECAST_HORIZON)
        dates = pd.date_range(start=s.index[-1] + pd.Timedelta(days=1), periods=FORECAST_HORIZON)

        fc_df = pd.DataFrame({"date": dates, "forecast": mean})
        if lo is not None:
            fc_df["lo"] = lo
            fc_df["hi"] = hi
        fc_df.to_parquet(OUT / f"forecast_{key}.parquet", index=False)

        # persist metadata for downstream (dashboard)
        meta = {
            "key": key,
            "model": model,
            "sarima_order": list(order) if order else None,
            "seasonal_period": SEASONAL_PERIOD,
            "trained_through": str(s.index[-1].date()),
            "horizon_days": FORECAST_HORIZON,
            "horizon_dates": [d.strftime("%Y-%m-%d") for d in dates],
            "forecast": [round(float(v), 1) for v in mean],
            "trailing_mean": float(s.tail(SEASONAL_PERIOD).mean()),
            "trailing_std": float(s.tail(SEASONAL_PERIOD).std()),
        }
        if lo is not None:
            meta["lo"] = [round(float(v), 1) for v in lo]
            meta["hi"] = [round(float(v), 1) for v in hi]
        with open(MODELS / f"model_meta_{key}.json", "w") as f:
            json.dump(meta, f, indent=2)

        forecast_out[key] = meta
        dates_out[key] = [d.strftime("%Y-%m-%d") for d in dates]

        fig, ax = plt.subplots()
        ax.plot(s.index, s.values, color="tab:blue", label="actual")
        ax.plot(dates, mean, color="tab:red", marker="o", label=f"{model} forecast")
        if lo is not None:
            ax.fill_between(dates, lo, hi, color="tab:red", alpha=0.2, label="95% CI")
        ax.set_title(f"{key.capitalize()} — 7-day forecast ({model})")
        ax.set_xlabel("Date"); ax.set_ylabel("Daily bookings")
        ax.legend()
        fig.tight_layout()
        fig.savefig(CHARTS / f"forecast_{key}.png"); plt.close(fig)

        print(f"  {key:<10} model={model:<15} " + ", ".join(f"{d[:10]}={v:,.0f}" for d, v in zip(dates_out[key], mean)))

    with open(OUT / "forecast_summary.json", "w") as f:
        json.dump(forecast_out, f, indent=2)
    print("\n-> output/forecast_{key}.parquet + models/model_meta_{key}.json + charts/forecast_{key}.png")


if __name__ == "__main__":
    main()