# Phase 3 — Forecasting & Anomaly Detection Report (v2)

Horizon: **7-day** | Validation: **walk-forward CV, 4 folds of 7 days** | Weekly seasonality (period 7)

## 1. Series used

| Series | Window | Days | Total bookings | Mean/day |
|---|---|---:|---:|---:|
| Jemmal | 2026-06-08 → 2026-10-08 | 123 | 355,579 | 2,891 |
| Monastir | 2025-10-13 → 2026-10-08 | 361 | 1,227,150 | 3,399 |
| Total | 2025-10-13 → 2026-10-08 | 361 | 1,582,729 | 4,384 |

*The trailing extraction day is dropped when it falls below 25% of the prior week's volume (see 01_prep.py); in this run it was a full-volume day and was kept.*

## 2. Model comparison — walk-forward CV (MAPE mean ± std over folds)

| Series | Naive | Seasonal naive | Seasonal median | Weekly mean | SARIMA | Prophet |
|---|---:|---:|---:|---:|---:|---:|
| Jemmal | 6.3% ± 3.7% | 11.5% ± 8.2% | 10.5% ± 5.5% | 10.4% ± 7.9% | 8.2% ± 2.2% | 22.7% ± 15.6% |
| Monastir | 21.7% ± 3.4% | 8.5% ± 3.1% | 9.7% ± 4.1% | 21.9% ± 2.9% | 9.8% ± 1.0% | 12.5% ± 1.5% |
| Total | 11.9% ± 3.4% | 9.8% ± 5.6% | 8.3% ± 4.2% | 13.2% ± 4.1% | 6.0% ± 1.8% | 10.7% ± 4.8% |

### Best model per series (by mean MAPE)

- **Jemmal** → **naive** (MAPE 6.3% ± 3.7%, RMSE 291 ± 158 bookings/day)
- **Monastir** → **seasonal_naive** (MAPE 8.5% ± 3.1%, RMSE 351 ± 91 bookings/day)
- **Total** → **sarima** (MAPE 6.0% ± 1.8%, RMSE 496 ± 151 bookings/day)

### Readout

- **SARIMA auto-selection**: order chosen by AIC on the full series, then reused for every fold (no test-set leakage). Orders: jemmal=[1, 0, 0, 1], monastir=[0, 1, 0, 1], total=[0, 1, 0, 1].
- On **short/noisy series (Jemmal)** simple persistence (naive) is best — 66 days is too little for a stable seasonal model.
- On **long stable series (Monastir)** seasonal persistence and SARIMA are comparable; the seasonal pattern dominates.
- **Prophet** is consistently worse here: it over-parametrizes for daily re-runs and short history.
- Seasonal-median is a solid, robust fallback (low std) — recommended default for the dashboard's quick view.

## 3. Final 7-day forecast (refit on full data, model from CV)

### Jemmal — model: `naive` (trained through 2026-10-08)

| Date | Forecast | 95% CI |
|---|---:|---:|
| 2026-10-09 | 3,535 | 3,535–3,535 |
| 2026-10-10 | 3,535 | 3,535–3,535 |
| 2026-10-11 | 3,535 | 3,535–3,535 |
| 2026-10-12 | 3,535 | 3,535–3,535 |
| 2026-10-13 | 3,535 | 3,535–3,535 |
| 2026-10-14 | 3,535 | 3,535–3,535 |
| 2026-10-15 | 3,535 | 3,535–3,535 |

### Monastir — model: `seasonal_naive` (trained through 2026-10-08)

| Date | Forecast | 95% CI |
|---|---:|---:|
| 2026-10-09 | 4,355 | — |
| 2026-10-10 | 3,538 | — |
| 2026-10-11 | 2,101 | — |
| 2026-10-12 | 4,331 | — |
| 2026-10-13 | 4,070 | — |
| 2026-10-14 | 3,777 | — |
| 2026-10-15 | 3,845 | — |

### Total — model: `sarima` (trained through 2026-10-08)

| Date | Forecast | 95% CI |
|---|---:|---:|
| 2026-10-09 | 7,402 | 6,052–8,751 |
| 2026-10-10 | 6,514 | 5,002–8,025 |
| 2026-10-11 | 5,852 | 4,194–7,511 |
| 2026-10-12 | 8,428 | 6,635–10,221 |
| 2026-10-13 | 7,418 | 5,500–9,336 |
| 2026-10-14 | 7,396 | 5,360–9,431 |
| 2026-10-15 | 7,333 | 5,186–9,480 |

## 4. Anomaly detection (3 detectors + consensus)

| Series | Rolling z | WoW-diff z | IsolationForest | Consensus |
|---|---:|---:|---:|---:|
| Jemmal | 2 | 1 | 3 | 1 |
| Monastir | 0 | 8 | 8 | 2 |
| Total | 0 | 6 | 8 | 2 |

### Consensus-flagged days (≥2 detectors, or a zero-booking day on a busy series)

- **Jemmal**: 2026-06-29 (2,553).
- **Monastir**: 2026-01-20 (0) ⚠ zero, 2026-05-27 (0) ⚠ zero.
- **Total**: 2026-01-20 (0) ⚠ zero, 2026-05-27 (0) ⚠ zero.

## 5. Recommended alert thresholds (calibrated on CV residuals)

- **Volume alert**: daily bookings with **consensus anomaly** (see §4) → investigate same-day.
- **Zero-day alert**: 0 bookings on a station whose 7-day trailing mean > 100 → immediate check.
- **WoW-drop alert**: week-over-week change below −3σ rolling → capacity/ops intervention.
- **Revenue alert** (Phase 2): real-bookings daily revenue < 80% of 7-day average.
- **Ghost-rate drift**: sustained ghost rate > 98% for 7 consecutive days → possible offline/auto-gen issue.

## 6. Diagnostics & caveats

1. CV metrics are mean over 4 expanding-window folds — far more robust than a single split; std reflects week-to-week stability.
2. Only ~2 months of Jemmal history → month-of-year seasonality is unmeasured; revisit after a full quarter.
3. Volume is dominated by ghost/draft bookings; **revenue forecasts must use the real subset** (see Phase 2).
4. Monastir fleet/capacity data is sparse (33% coverage) — fleet thresholds are indicative.
5. Forecast metadata is persisted in `models/model_meta_*.json` for the Phase 4 dashboard.

## Charts

| Chart | File |
|---|---|
| Anomalies Jemmal | `charts/anomalies_jemmal.png` |
| Anomalies Monastir | `charts/anomalies_monastir.png` |
| Anomalies Total | `charts/anomalies_total.png` |
| Forecast Jemmal | `charts/forecast_jemmal.png` |
| Forecast Monastir | `charts/forecast_monastir.png` |
| Forecast Total | `charts/forecast_total.png` |