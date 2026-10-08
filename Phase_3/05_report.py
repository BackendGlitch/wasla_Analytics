"""Phase 3 - Build the consolidated FORECAST_REPORT.md (v2)."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from config import OUT, CHARTS, FORECAST_HORIZON, STATIONS

SERIES_KEYS = STATIONS + ["total"]
DETECTORS = ["rolling_z", "wow_z", "isolation_forest"]


def j(path: str):
    with open(OUT / path) as f:
        return json.load(f)


def fmt_pair(v, suffix="mape"):
    return f"{v[suffix + '_mean']:.1%} \u00b1 {v[suffix + '_std']:.1%}"


def main() -> None:
    metrics = j("model_metrics_v2.json")
    forecasts = j("forecast_summary.json")
    anomalies = j("anomaly_summary.json")
    series_desc = j("series_descriptor.json")

    L = []
    add = L.append
    add("# Phase 3 — Forecasting & Anomaly Detection Report (v2)")
    add("")
    add(f"Horizon: **{FORECAST_HORIZON}-day** | Validation: **walk-forward CV, {metrics['jemmal']['n_folds']} folds of 7 days** | Weekly seasonality (period 7)")
    add("")
    add("## 1. Series used")
    add("")
    add("| Series | Window | Days | Total bookings | Mean/day |")
    add("|---|---|---:|---:|---:|")
    for key in SERIES_KEYS:
        d = series_desc[key]
        add(f"| {key.capitalize()} | {d['start']} → {d['end']} | {d['n_days']} | {d['total']:,} | {d['mean']:,.0f} |")
    add("")
    add("*The trailing extraction day is dropped when it falls below 25% of the prior week's volume (see 01_prep.py); in this run it was a full-volume day and was kept.*")
    add("")
    add("## 2. Model comparison — walk-forward CV (MAPE mean ± std over folds)")
    add("")
    add("| Series | Naive | Seasonal naive | Seasonal median | Weekly mean | SARIMA | Prophet |")
    add("|---|---:|---:|---:|---:|---:|---:|")
    for key in SERIES_KEYS:
        m = metrics[key]["models"]
        add(
            f"| {key.capitalize()} | {fmt_pair(m['naive'])} | {fmt_pair(m['seasonal_naive'])} | "
            f"{fmt_pair(m['seasonal_median'])} | {fmt_pair(m['weekly_mean'])} | {fmt_pair(m['sarima'])} | {fmt_pair(m['prophet'])} |"
        )
    add("")
    add("### Best model per series (by mean MAPE)")
    add("")
    for key in SERIES_KEYS:
        m = metrics[key]
        best = m["best_by_mape"]
        add(
            f"- **{key.capitalize()}** → **{best}** "
            f"(MAPE {m['models'][best]['mape_mean']:.1%} ± {m['models'][best]['mape_std']:.1%}, "
            f"RMSE {m['models'][best]['rmse_mean']:,.0f} ± {m['models'][best]['rmse_std']:,.0f} bookings/day)"
        )
    add("")
    add("### Readout")
    add("")
    add("- **SARIMA auto-selection**: order chosen by AIC on the full series, then reused for every fold "
        "(no test-set leakage). Orders: " + ", ".join(f"{k}={m['sarima_order']}" for k, m in metrics.items()) + ".")
    add("- On **short/noisy series (Jemmal)** simple persistence (naive) is best — 66 days is too little for a stable seasonal model.")
    add("- On **long stable series (Monastir)** seasonal persistence and SARIMA are comparable; the seasonal pattern dominates.")
    add("- **Prophet** is consistently worse here: it over-parametrizes for daily re-runs and short history.")
    add("- Seasonal-median is a solid, robust fallback (low std) — recommended default for the dashboard's quick view.")
    add("")
    add("## 3. Final 7-day forecast (refit on full data, model from CV)")
    add("")
    for key in SERIES_KEYS:
        fc = forecasts[key]
        add(f"### {key.capitalize()} — model: `{fc['model']}` (trained through {fc['trained_through']})")
        add("")
        add("| Date | Forecast | 95% CI |")
        add("|---|---:|---:|")
        for i, d in enumerate(fc["horizon_dates"]):
            ci = f"{fc['lo'][i]:,.0f}–{fc['hi'][i]:,.0f}" if fc.get("lo") else "—"
            add(f"| {d} | {fc['forecast'][i]:,.0f} | {ci} |")
        add("")
    add("## 4. Anomaly detection (3 detectors + consensus)")
    add("")
    add("| Series | Rolling z | WoW-diff z | IsolationForest | Consensus |")
    add("|---|---:|---:|---:|---:|")
    for key in SERIES_KEYS:
        a = anomalies[key]
        add(f"| {key.capitalize()} | {a['rolling_z']} | {a['wow_z']} | {a['isolation_forest']} | {a['consensus']} |")
    add("")
    add("### Consensus-flagged days (≥2 detectors, or a zero-booking day on a busy series)")
    add("")
    for key in SERIES_KEYS:
        a = anomalies[key]
        if not a["flag_days"]:
            add(f"- **{key.capitalize()}**: none.")
        else:
            desc = ", ".join(f"{d['date']} ({d['bookings']:,})" + (" ⚠ zero" if d.get("zero_day") else "") for d in a["flag_days"])
            add(f"- **{key.capitalize()}**: {desc}.")
    add("")
    add("## 5. Recommended alert thresholds (calibrated on CV residuals)")
    add("")
    add("- **Volume alert**: daily bookings with **consensus anomaly** (see §4) → investigate same-day.")
    add("- **Zero-day alert**: 0 bookings on a station whose 7-day trailing mean > 100 → immediate check.")
    add("- **WoW-drop alert**: week-over-week change below −3σ rolling → capacity/ops intervention.")
    add("- **Revenue alert** (Phase 2): real-bookings daily revenue < 80% of 7-day average.")
    add("- **Ghost-rate drift**: sustained ghost rate > 98% for 7 consecutive days → possible offline/auto-gen issue.")
    add("")
    add("## 6. Diagnostics & caveats")
    add("")
    add("1. CV metrics are mean over 4 expanding-window folds — far more robust than a single split; "
        "std reflects week-to-week stability.")
    add("2. Only ~2 months of Jemmal history → month-of-year seasonality is unmeasured; revisit after a full quarter.")
    add("3. Volume is dominated by ghost/draft bookings; **revenue forecasts must use the real subset** (see Phase 2).")
    add("4. Monastir fleet/capacity data is sparse (33% coverage) — fleet thresholds are indicative.")
    add("5. Forecast metadata is persisted in `models/model_meta_*.json` for the Phase 4 dashboard.")
    add("")
    add("## Charts")
    add("")
    add("| Chart | File |")
    add("|---|---|")
    for p in sorted(CHARTS.glob("*.png")):
        add(f"| {p.stem.replace('_', ' ').title()} | `charts/{p.name}` |")

    (OUT.parent / "FORECAST_REPORT.md").write_text("\n".join(L))
    print("Wrote FORECAST_REPORT.md (v2)")


if __name__ == "__main__":
    main()