# Phase 2 — Statistical Analysis Report

Generated from the Phase_1 clean/features layers (/home/ivan/red_eye/Internship/Phase_1).

## 1. Passenger flow

| Station | Total bookings | Real (sold) | Ghost rate | Avg/day | Peak hour | Peak/off-peak |
|---|---|---:|---:|---:|---:|---:|
| Jemmal | 355,579 | 94,193 | 73.5% | 3,175 | 07h | 2.90x |
| Monastir | 1,227,150 | 10,401 | 99.2% | 3,428 | 12h | 3.24x |

- Jemmal peaks in the **morning (06h)**; Monastir in the **midday (12h)** rush.
- Ghost rate is ~3x higher at Monastir; treat flow analytics on the real subset separately.

## 2. Revenue (dual definition)

**Definition A (passenger-paid)** = SUM(`total_amount`) — base fare + service fee (what the passenger pays).
**Definition B (station fee)** = seats × 0.15 TND + day passes × 2.0 TND — what the station keeps.

| Station | Passenger-paid | Station fee (bookings) | Day-pass fee | Real-bookings rev |
|---|---:|---:|---:|---:|
| Jemmal | 956,248 | 53,383 | 10,292 | 436,300 |
| Monastir | 2,470,831 | 184,346 | 66,366 | 20,567 |

Consolidated: passenger-paid **3,427,079 TND** vs station fee **237,729 TND** — the 6.9% share stays with the station; the rest goes to drivers. Real (sold) bookings contribute only a fraction of passenger-paid totals because ghosts dominate.

## 3. Route performance

| Station | Route | Bookings | Revenue (TND) | Avg ticket | Ghost rate |
|---|---|---:|---:|---:|---:|
| Jemmal | Monastir | 144,485 | 281,855 | 1.95 | 99.7% |
| Jemmal | Sousse | 87,670 | 249,765 | 2.85 | 28.5% |
| Jemmal | Ksar Hlel | 82,452 | 119,567 | 1.45 | 99.9% |
| Jemmal | Souassi | 30,953 | 147,084 | 4.75 | 32.0% |
| Jemmal | Tunis | 9,952 | 157,728 | 15.85 | 1.0% |
| Jemmal | Unknown | 67 | 250 | 3.73 | 0.0% |
| Monastir | Jemmal | 508,292 | 992,149 | 1.95 | 99.9% |
| Monastir | Ksar Hlel | 439,344 | 835,950 | 1.90 | 100.0% |
| Monastir | Moknin | 186,105 | 410,102 | 2.20 | 100.0% |
| Monastir | Teboulba | 83,424 | 213,072 | 2.55 | 100.0% |
| Monastir | Unknown | 9,985 | 19,558 | 1.96 | 0.0% |

- **Jemmal→Tunis** is the highest-value route: 4,349 bookings / 70,882 TND (16.30 TND avg, 1.7% ghosts).
- **Jemmal→Souassi** second-highest avg ticket (4.75 TND) with 58% ghosts.
- **Monastir** routes are almost entirely ghost (99.9%); real volume is negligible — likely drafts/offline.

## 4. Fleet utilization

| Station | Trips | Vehicles seen | Trips/vehicle | Avg load factor | Capacity coverage | Window |
|---|---:|---:|---:|---:|---:|---|
| Jemmal | 12,948 | 160 | 80.0 | 90.9% | 99% | 2026-06-07 → 2026-10-08 |
| Monastir | 1,261 | 112 | 9.2 | 98.5% | 33% | 2025-10-19 → 2026-09-17 |

- Average **load factor ~90%+** at both stations — vehicles are dispatched near-full.
- Jemmal fills `booked_seats`, Monastir fills `seats_booked`; load factor uses the combined seat count. Monastir only records `vehicle_capacity` on 33% of trips — treat its fleet numbers as indicative, not exhaustive.

## 5. Cancellations

| Station | Cancelled | Rate | Top reason |
|---|---:|---:|---|
| Jemmal | 456 | 0.128% | cancel_last_operator_no_trip |
| Monastir | 45 | 0.004% | test cancel |

- Cancellation is **near-zero** in production (0.005%); cancellation analytics is not actionable until more data exists.

## 6. Key implications for forecasting (Phase 3)

1. **Forecast on ghost/all bookings for volume** (flow is generated even for drafts) but **forecast revenue on the real subset** — mixing them distorts revenue prediction by ~10-15x.
2. Data is only ~2 months old at Jemmal → **lean on hour-of-day / day-of-week seasonality**, use a 7-day horizon.
3. Monastir ghost rate (~99%) means its 'revenue' is not meaningful yet — treat Monastir revenue forecasts with caution.
4. Strong morning (Jemmal) / midday (Monastir) peaks → capacity planning should align dispatch to those windows.

## Charts

| Chart | File |
|---|---|
| Cancellations | `charts/cancellations.png` |
| Fleet Load Factor | `charts/fleet_load_factor.png` |
| Flow Daily | `charts/flow_daily.png` |
| Flow Hourly | `charts/flow_hourly.png` |
| Flow Weekday | `charts/flow_weekday.png` |
| Revenue By Route | `charts/revenue_by_route.png` |
| Revenue Daily | `charts/revenue_daily.png` |
| Revenue Real Vs Ghost | `charts/revenue_real_vs_ghost.png` |
| Route Performance | `charts/route_performance.png` |