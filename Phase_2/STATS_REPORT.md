# Phase 2 — Statistical Analysis Report

Generated from the Phase_1 clean/features layers (/home/ivan/red_eye/Internship/Phase_1).

## 1. Passenger flow

| Station | Total bookings | Real (sold) | Ghost rate | Avg/day | Peak hour | Peak/off-peak |
|---|---|---:|---:|---:|---:|---:|
| Jemmal | 149,969 | 26,629 | 82.2% | 2,727 | 06h | 3.32x |
| Monastir | 1,038,329 | 10,401 | 99.0% | 3,461 | 12h | 3.28x |

- Jemmal peaks in the **morning (06h)**; Monastir in the **midday (12h)** rush.
- Ghost rate is ~3x higher at Monastir; treat flow analytics on the real subset separately.

## 2. Revenue (dual definition)

**Definition A (passenger-paid)** = SUM(`total_amount`) — base fare + service fee (what the passenger pays).
**Definition B (station fee)** = seats × 0.15 TND + day passes × 2.0 TND — what the station keeps.

| Station | Passenger-paid | Station fee (bookings) | Day-pass fee | Real-bookings rev |
|---|---:|---:|---:|---:|
| Jemmal | 408,368 | 22,542 | 3,276 | 143,991 |
| Monastir | 2,090,687 | 156,023 | 58,152 | 20,567 |

Consolidated: passenger-paid **2,499,055 TND** vs station fee **178,565 TND** — the 7.1% share stays with the station; the rest goes to drivers. Real (sold) bookings contribute only a fraction of passenger-paid totals because ghosts dominate.

## 3. Route performance

| Station | Route | Bookings | Revenue (TND) | Avg ticket | Ghost rate |
|---|---|---:|---:|---:|---:|
| Jemmal | Monastir | 60,918 | 118,899 | 1.95 | 99.3% |
| Jemmal | Sousse | 36,681 | 104,447 | 2.85 | 55.7% |
| Jemmal | Ksar Hlel | 34,533 | 50,084 | 1.45 | 100.0% |
| Jemmal | Souassi | 13,421 | 63,807 | 4.75 | 58.2% |
| Jemmal | Tunis | 4,349 | 70,882 | 16.30 | 1.7% |
| Jemmal | Unknown | 67 | 250 | 3.73 | 0.0% |
| Monastir | Jemmal | 429,293 | 838,101 | 1.95 | 99.9% |
| Monastir | Ksar Hlel | 372,625 | 709,184 | 1.90 | 100.0% |
| Monastir | Moknin | 155,867 | 343,578 | 2.20 | 100.0% |
| Monastir | Teboulba | 70,559 | 180,267 | 2.55 | 100.0% |
| Monastir | Unknown | 9,985 | 19,558 | 1.96 | 0.0% |

- **Jemmal→Tunis** is the highest-value route: 4,349 bookings / 70,882 TND (16.30 TND avg, 1.7% ghosts).
- **Jemmal→Souassi** second-highest avg ticket (4.75 TND) with 58% ghosts.
- **Monastir** routes are almost entirely ghost (99.9%); real volume is negligible — likely drafts/offline.

## 4. Fleet utilization

| Station | Trips | Vehicles seen | Trips/vehicle | Avg load factor | Capacity coverage | Window |
|---|---:|---:|---:|---:|---:|---|
| Jemmal | 3,732 | 136 | 26.4 | 90.4% | 96% | 2026-06-07 → 2026-08-12 |
| Monastir | 1,260 | 117 | 9.1 | 98.8% | 33% | 2025-10-19 → 2026-04-20 |

- Average **load factor ~90%+** at both stations — vehicles are dispatched near-full.
- Jemmal fills `booked_seats`, Monastir fills `seats_booked`; load factor uses the combined seat count. Monastir only records `vehicle_capacity` on 33% of trips — treat its fleet numbers as indicative, not exhaustive.

## 5. Cancellations

| Station | Cancelled | Rate | Top reason |
|---|---:|---:|---|
| Jemmal | 70 | 0.047% | cancel_last_operator_no_trip |
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