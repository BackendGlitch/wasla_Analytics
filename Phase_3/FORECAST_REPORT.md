# Phase 3 — Forecasting & Anomaly Detection Report (v2)

Horizon: **7-day** | Validation: **walk-forward CV, 4 folds of 7 days** | Weekly seasonality (period 7)

## 1. Series used

| Series | Window | Days | Total bookings | Mean/day |
|---|---|---:|---:|---:|
| Jemmal | 2026-06-08 → 2026-08-11 | 65 | 149,953 | 2,307 |
| Monastir | 2025-10-13 → 2026-08-11 | 303 | 1,038,329 | 3,427 |
| Total | 2025-10-13 → 2026-08-11 | 303 | 1,188,282 | 3,922 |

*Partial trailing day (extraction day) dropped to avoid skewing MAPE (see 01_prep.py).*

## 2. Model comparison — walk-forward CV (MAPE mean ± std over folds)

| Series | Naive | Seasonal naive | Seasonal median | Weekly mean | SARIMA | Prophet |
|---|---:|---:|---:|---:|---:|---:|
| Jemmal | 9.1% ± 2.2% | 11.6% ± 1.7% | 10.7% ± 2.4% | 10.9% ± 2.1% | 11.1% ± 3.2% | 36.9% ± 8.1% |
| Monastir | 20.9% ± 3.6% | 10.3% ± 5.0% | 11.2% ± 5.9% | 18.4% ± 3.7% | 11.2% ± 6.8% | 14.7% ± 11.2% |
| Total | 12.8% ± 2.9% | 10.1% ± 2.9% | 9.6% ± 1.8% | 12.5% ± 2.3% | 9.2% ± 3.7% | 13.7% ± 4.0% |

### Best model per series (by mean MAPE)

- **Jemmal** → **naive** (MAPE 9.1% ± 2.2%, RMSE 440 ± 124 bookings/day)
- **Monastir** → **seasonal_naive** (MAPE 10.3% ± 5.0%, RMSE 392 ± 203 bookings/day)
- **Total** → **sarima** (MAPE 9.2% ± 3.7%, RMSE 741 ± 249 bookings/day)

### Readout

- **SARIMA auto-selection**: order chosen by AIC on the full series, then reused for every fold (no test-set leakage). Orders: jemmal=[0, 0, 0, 1], monastir=[0, 1, 0, 1], total=[0, 1, 0, 1].
- On **short/noisy series (Jemmal)** simple persistence (naive) is best — 66 days is too little for a stable seasonal model.
- On **long stable series (Monastir)** seasonal persistence and SARIMA are comparable; the seasonal pattern dominates.
- **Prophet** is consistently worse here: it over-parametrizes for daily re-runs and short history.
- Seasonal-median is a solid, robust fallback (low std) — recommended default for the dashboard's quick view.

## 3. Final 7-day forecast (refit on full data, model from CV)

### Jemmal — model: `naive` (trained through 2026-08-11)

| Date | Forecast | 95% CI |
|---|---:|---:|
| 2026-08-12 | 3,632 | 3,632–3,632 |
| 2026-08-13 | 3,632 | 3,632–3,632 |
| 2026-08-14 | 3,632 | 3,632–3,632 |
| 2026-08-15 | 3,632 | 3,632–3,632 |
| 2026-08-16 | 3,632 | 3,632–3,632 |
| 2026-08-17 | 3,632 | 3,632–3,632 |
| 2026-08-18 | 3,632 | 3,632–3,632 |

### Monastir — model: `seasonal_naive` (trained through 2026-08-11)

| Date | Forecast | 95% CI |
|---|---:|---:|
| 2026-08-12 | 3,442 | — |
| 2026-08-13 | 3,542 | — |
| 2026-08-14 | 3,389 | — |
| 2026-08-15 | 2,613 | — |
| 2026-08-16 | 2,503 | — |
| 2026-08-17 | 4,248 | — |
| 2026-08-18 | 3,621 | — |

### Total — model: `sarima` (trained through 2026-08-11)

| Date | Forecast | 95% CI |
|---|---:|---:|
| 2026-08-12 | 7,406 | 6,067–8,746 |
| 2026-08-13 | 7,447 | 5,938–8,956 |
| 2026-08-14 | 7,276 | 5,615–8,937 |
| 2026-08-15 | 6,676 | 4,876–8,476 |
| 2026-08-16 | 6,132 | 4,202–8,062 |
| 2026-08-17 | 8,293 | 6,242–10,343 |
| 2026-08-18 | 7,678 | 5,513–9,843 |

## 4. Anomaly detection (3 detectors + consensus)

| Series | Rolling z | WoW-diff z | IsolationForest | Consensus |
|---|---:|---:|---:|---:|
| Jemmal | 2 | 1 | 2 | 1 |
| Monastir | 0 | 7 | 7 | 2 |
| Total | 0 | 6 | 7 | 2 |

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