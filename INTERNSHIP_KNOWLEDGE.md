# Wasla Analytics Internship — Knowledge File

Internal knowledge base for the **Transport Analytics & Operations Intelligence** internship project at Backend Glitch Inc.

## 1. Project Overview

An internship building the **analytics layer** on top of the live **Wasla** transport management platform. The goal is to transform raw operational data into actionable business intelligence for station operators and management.

- **Organization**: Backend Glitch Inc. (backendglitch.com)
- **Project**: Wasla — Transport Analytics Engine
- **Student**: Yasmine Ghomrassi (Master's Degree, Statistics and Data Science, University of Palermo, Italy)
- **Company supervisor**: Mr. Samer Gassouma (CEO)
- **Type**: In-person internship (~3 months)
- **Live stations**: Monastir Centre (hub), Jammel-Monastir — Ksar Hlel planned, further expansion expected

### What Wasla handles operationally
Passenger bookings, vehicle dispatching (louages / shared 8-seat taxis), day pass management, route scheduling, ticket printing, staff shift tracking, and real-time station monitoring.

Platform in production since April 2026. Current fleet ≈ **113 active vehicles (8-seat each)** serving **5 destination routes**: Ksar Hlel, Tunis, Sousse, Souassi, Monastir.

## 2. The Data

Intern works with the **live production PostgreSQL database** on the station servers (behind Tailscale).

| Table | Status | Content |
|---|---|---|
| `bookings` | Active | Passenger bookings: status, amount, payment method, timestamps, destination |
| `day_passes` | Active | Station entry passes with validity windows |
| `trips` | Active | Vehicle departures: license plate, destination, seat count |
| `vehicles` | ~113 registered | Fleet registry (8-seat capacity each) |
| `stations` | 2 live | Monastir Centre, Jammel-Monastir |
| `routes` | 5 | Ksar Hlel, Tunis, Sousse, Souassi, Monastir |
| `staff` | Active | Station agents with shift tracking |
| `staff_daily_statistics` | **Legacy** | Per-agent summaries — **no longer written** (see §6) |
| `station_daily_statistics` | **Legacy** | Daily station aggregates — **no longer written** (see §6) |
| `print_jobs` | Active | Ticket printing with audit trail |

All monetary values are in **Tunisian Dinar (TND)**. Data spans from April 2026 to present, growing daily.

### 2.1 Current data state (snapshot, Jemmal station, Jun–Aug 2026)

| Table | Rows | First | Last |
|---|---|---|---|
| `bookings` | ~150,000 | 08 Jun 2026 | 12 Aug 2026 |
| `trips` | 3,729 | 07 Jun 2026 | 12 Aug 2026 |
| `day_passes` | 1,636 | 07 Jun 2026 | 12 Aug 2026 |
| `print_jobs` | 4,532 | 07 Jun 2026 | 11 Aug 2026 |
| `staff` | 14 active (not 6 as the brief claims) |
| `subscriptions` | 0 (feature not in use at Jemmal) |

#### Revenue by destination (ACTIVE bookings, passenger-paid total = base + fee)

| Destination | Bookings | Seats | Revenue (base+fee) |
|---|---|---|---|
| Monastir (`st_monastir`) | 60,887 | 60,897 | 118,749 TND |
| Sousse (`st_sousse`) | 36,641 | 36,648 | 104,325 TND |
| Ksar Hlel (`st_ksar_hellal`) | 34,517 | 34,524 | 50,060 TND |
| Souassi (`st_souassi`) | 13,410 | 13,417 | 63,731 TND |
| Tunis (`st_maghreb_nabeul`) | 4,284 | 4,476 | 69,378 TND |

**Station-fee-only comparison** (`staff_transaction_log`): 150,990 `SEAT_BOOKING` rows / **27,487 TND** (0.15 TND/seat). Passenger-paid total ≈ **400k TND** vs station commission ≈ **27.5k TND** — the two-revenue gap is large and material (see §6.1).

#### Growth pattern (visible scaling)

- **Jun 2026**: ~5.9k bookings / 14k TND
- **Jul 2026**: ~104k bookings / 283k TND (≈18× growth — platform scaled up)
- **Aug 2026 (partial)**: ~39.6k bookings / 109k TND

#### Peak hours (morning rush, all stations)

- 06:00 (~19k), 07:00 (~17k), 08:00 (~17.5k), 09:00 (~15k) — heavy morning peak, tailing off through the day.

#### Implications for the analytics work

- Rich, real data: 150k bookings, clear day-parting, 5-destination split, per-staff attribution — enough for EDA, forecasting, and anomaly detection.
- **Caution**: only ~2 months of history (thin for month-of-year seasonality) → models should lean on hour-of-day / day-of-week patterns; forecast on 7-day horizon first.
- `subscriptions` is empty at Jemmal → that revenue line will be zero; don't model it until data exists.

## 3. Project Pipeline

| Stage | What Happens |
|---|---|
| Data Exploration | Connect to live DB, explore schema/distributions, understand the business domain |
| Data Cleaning | Handle anomalies, normalise timestamps, engineer features (hour, day-of-week, seasonality) |
| Statistical Analysis | Passenger flow patterns, revenue trends, peak hours, route performance, fleet utilization |
| ML & Forecasting | Predict daily passenger volume, forecast revenue, detect booking anomalies |
| Dashboard | Real-time operations dashboard with KPIs, charts, drill-down |
| Cloud Deployment | Ship analytics stack (API + dashboard) to the production VPS |

### 3.1 Data Exploration & Cleaning
- Connect to the production database, explore schema and distributions
- Understand business logic: booking flow, status semantics, trips/vehicles/routes relationship
- Profile data: distributions, missing values, outliers
- Engineer time features: hour of day, day of week, month, season, holiday markers
- Produce a clean, analytics-ready dataset

### 3.2 Statistical Analysis
- **Passenger flow** — hourly/daily booking volume, weekday vs weekend, seasonal trends
- **Revenue analytics** — daily trends, average per booking, per-route contribution
- **Peak hours** — busiest hours per station, peak-to-off-peak ratio
- **Route performance** — 5 destinations by volume, revenue, growth
- **Fleet utilization** — active vehicles/day, trips per vehicle, average load factor
- **Cancellation analysis** — rate, reasons, timing patterns

### 3.3 Machine Learning & Forecasting
- Time series forecasting for passenger volume (ARIMA/SARIMA, Prophet; statsmodels/scikit-learn)
- Passenger volume prediction (7-day / 30-day horizons)
- Anomaly detection (statistical thresholds / Isolation Forest / statistical process control)
- Model validation: MAPE, RMSE, precision/recall; alert threshold calibration

### 3.4 Dashboard (Next.js)
| Module | What It Shows |
|---|---|
| Overview | Today's bookings, revenue, active vehicles, passengers per station |
| Passenger Flow | Hourly + daily booking trends, peak hour indicators |
| Revenue Dashboard | Daily/weekly/monthly revenue, per-route breakdown, growth trends |
| Fleet Monitor | Active vehicles, trips completed, load factor, utilization |
| Forecast View | Predicted vs actual, next 7-day forecast, anomaly flags |
| Station Drill-down | Monastir vs Jammel comparison |

### 3.5 Cloud Deployment
- Containerise analytics API (FastAPI) + dashboard (Next.js) with Docker
- Nginx reverse proxy for the analytics subdomain
- Connect to live database (read-only replica or read-only credentials)
- Automated data refresh (daily aggregation jobs)

## 4. Technology Stack

| Component | Technology |
|---|---|
| Database | PostgreSQL (production, live operational data) |
| Data Processing | Python — pandas, numpy, SQLAlchemy |
| Statistical Analysis | Python — matplotlib, seaborn, scipy |
| Forecasting | Prophet / statsmodels / scikit-learn |
| Anomaly Detection | scikit-learn (IsolationForest, statistical thresholds) |
| Analytics API | Python — FastAPI |
| Dashboard | Next.js (React) with Recharts / Chart.js |
| Containerisation | Docker + docker-compose |
| Reverse Proxy | Nginx |
| Hosting | Linux VPS (existing Wasla infrastructure) |

## 5. Expected Deliverables

1. EDA report with visualisations (passenger flow, revenue, routes, fleet)
2. Cleaned and feature-engineered analytics dataset
3. Passenger volume forecasting model with documented accuracy metrics
4. Anomaly detection system with alert thresholds
5. Functional operations dashboard (Next.js) with real-time metrics
6. Docker-deployed analytics stack on the Wasla VPS
7. Final technical report (methodology, findings, recommendations)

## 6. Technical Gotchas — Real-System Corrections

**Important**: the brief describes the system somewhat idealised. These are the corrections every design decision must respect, verified against the actual codebase:

### 6.1 Two different definitions of "revenue" exist — pick one explicitly
- The **statistics-service** computes station income as **station fee only** = `SUM(seats × routes.service_fee)` (default **0.15 TND/seat**). Day passes = count × 2.0 TND. Subscriptions come from `staff_transaction_log`.
- The **public API** (`publicapi`) computes today's revenue as `SUM(total_amount)` from bookings — which includes **base price + service fee** (i.e., what the passenger paid, not what the station keeps).
- Base fare goes to the **driver/vehicle**, not the station. Any analytics must state clearly which "revenue" is being reported, or numbers will appear inconsistent.

### 6.2 `staff_daily_statistics` / `station_daily_statistics` are dead tables
- The brief lists them as "Active", but **no Go code writes to them anymore**. Income is computed **live per request** from `bookings`, `day_passes`, `trips`, `staff_transaction_log`.
- Do not design the analytics around these tables — use the live queries / source tables directly.

### 6.3 Staff count
- The brief claims "6 active staff", but the real DB contains **more than a dozen staff members** (e.g. Fatma Mekni, Mohamed ali Mokni, and many others). Factor this into per-staff analysis.

### 6.4 Access & security
- Station DBs live on the **station servers behind Tailscale**. Use **read-only credentials / a read-only replica** for the intern.
- No write access to production. Deployments go through this repo → SCP to servers (servers cannot reach GitHub directly).

### 6.5 Overlap with the existing ERP dashboard
- There is already an **operations/BI dashboard** at `admin.dhraief.live` (ERP, multi-station, real-time WS, revenue reports, PDF/XLSX export) fed by the same underlying data.
- Recommended split: **ERP owns live operations BI; this internship owns forecasting + anomaly detection + the analytics dataset**. Define coexistence explicitly to avoid duplicate work.

### 6.6 In-flight feature (related)
- A **daily revenue reconciliation** feature is under discussion: supervisors may correct daily totals when power cuts / extra ticket prints cause booked revenue to differ from actual cash. Once landed, it affects how "actual income" should be treated in analytics.

## 7. Operational Requirements & Risks

- **Read-only DB role** for the intern — never write access.
- **Deployment path**: read-only replica or read-only credentials; automated daily refresh with a defined cadence.
- **Forecast fallback**: if model accuracy targets are not met in the ML phase, define a fallback (e.g. simple seasonal baseline) rather than blocking the dashboard.
- **Data staleness**: the "cleaned dataset" can go stale; document the refresh/versioning strategy.
- **Post-internship continuity**: models and dashboards must remain maintainable after the internship ends.

## 8. References

- Project brief: `document.pdf`
- Training plan (signed): `document1.pdf`
- Wasla platform knowledge: repo root `wasla-knowledge.md`, `wasla-session.md`
- Backend (statistics/revenue source of truth): `wasla_backend/internal/statistics/`, `wasla_backend/internal/booking/`
- Existing ERP analytics: `erp/` (backend `internal/modules/{revenue,analytics,dashboard}/`, frontend `erp/frontend/`)