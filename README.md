# Wasla Analytics — Transport Analytics & Operations Intelligence

Analytics layer on top of the live **Wasla** transport-management platform. Wasla is
built by **Backend Glitch Inc.** (a software company working mainly on fintech,
crypto and backend solutions) for its client **Dhraief Service de Transport**
(https://www.dhraief.live/), the operator of the Monastir Centre and Jammel-Monastir
stations.

This repository contains: data extraction & cleaning from the two live stations,
statistical analysis, demand forecasting, anomaly detection, an operations dashboard,
and a read-only analytics API with a live WebSocket feed.

**Intern:** Yasmine Ghomrassi — Master's in Statistics and Data Science, University of Palermo
**Supervisor:** Mr. Samer Gassouma (CEO, Backend Glitch Inc.) · **Location:** Monastir, Tunisia · **Period:** 1 July – 25 September 2026

## Live platform

🔗 **Dashboard on Vercel:** https://wasla-analytics.vercel.app

## What's inside

```
Production Postgres (Jemmal + Monastir)
   └─ SSH tunnels (read-only)
Phase_1/  extraction → cleaning → features (parquet) + EDA
Phase_2/  statistics: flow, revenue (dual definition), routes, fleet
Phase_3/  forecasting (walk-forward CV) + 3-detector anomaly consensus
analytics_dashboard/  Next.js dashboard, 7 views, dark theme, mock ⇄ live API modes
analytics_api/        FastAPI, REST endpoints + WS /ws/live (60s live tick)
report/               internship report (LaTeX + PDF)
```

## Headline numbers (extracted 2026-10-08)

| | |
|---|---|
| Bookings | **1,582,729** (Jemmal 355,579 · Monastir 1,227,150) |
| Real vs ghost | 6.6% real (sold) · 93.4% ghost drafts |
| Revenue — passenger-paid | **3,427,079 TND** |
| Revenue — station fee | **237,729 TND** (6.9% share) |
| Forecast MAPE (walk-forward CV) | 6.0% total (SARIMA) · 6.3% Jemmal (naive) · 8.5% Monastir (seasonal naive) |
| Peaks | Jemmal 07h · Monastir 12h |

## Dashboard

![Overview](analytics_dashboard/docs/screenshots/1-overview.png)
![Forecast](analytics_dashboard/docs/screenshots/6-forecast.png)
![Revenue](analytics_dashboard/docs/screenshots/3-revenue.png)

More views in [`analytics_dashboard/docs/screenshots/`](analytics_dashboard/docs/screenshots/).

## Architecture

<p align="center">
  <img src="analytics_dashboard/docs/architecture.png" alt="Architecture" width="640" />
</p>

```
Jemmal DB ──┐                                            ┌── Monastir DB
            └─> SSH tunnels (read-only) ─> Phase 1 Data ─> Phase 2 Stats ─> Phase 3 ML
                                                                                │
                        live 60 s count/sum queries <──────┐                    │
                                                            │                    ▼
                       FastAPI (REST + WS) <────────────────┴───── Analytics artifacts
                            │  REST + WS live tick
                            ▼
                      Next.js dashboard (7 views)
```

## Run it locally, step by step

### Prerequisites

- Python 3.12 with `pandas, numpy, scipy, statsmodels, prophet, scikit-learn, matplotlib, seaborn, pyarrow, sqlalchemy, psycopg2-binary`
- Node.js 24 + pnpm
- Docker + docker compose (optional, for the containerised demo)
- SSH access to the station servers (read-only)

### 1. Open the SSH tunnels to the station databases

```bash
# Jemmal station
ssh -fN -L 15432:localhost:5432 server@100.72.205.59
# Monastir station
ssh -fN -L 15433:localhost:5432 ste@100.123.86.114
```

(Read-only SELECTs only. See `Phase_1/NOTES.md` for credentials and gotchas.)

### 2. Re-run the data pipeline (extraction → cleaning → features → stats → ML)

```bash
# Extract the 8 tables per station to parquet (~25 min for Monastir)
cd Phase_1/scripts
python3 01_extract.py jemmal
python3 01_extract.py monastir

# Clean + features + EDA
cd .. && python3 02_clean.py && python3 03_features.py && python3 04_eda.py

# Statistics
cd ../Phase_2
python3 01_flow.py && python3 02_revenue.py && python3 03_routes.py && python3 04_fleet.py && python3 05_report.py

# Forecast + anomalies
cd ../Phase_3
python3 01_prep.py && python3 02_models.py && python3 03_forecast.py && python3 04_anomalies.py && python3 05_report.py
```

### 3. Run the dashboard (mock mode first, no API needed)

```bash
cd analytics_dashboard
python3 scripts/gen_mocks.py          # build the static data the dashboard reads
python3 scripts/verify_mocks.py       # verify every mock number against the parquet
pnpm install
NEXT_PUBLIC_USE_MOCK=1 pnpm dev       # http://localhost:3000
```

### 4. Run the API and switch the dashboard to live mode

```bash
cd analytics_api
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
JEM_DB_URL='postgresql+psycopg2://wasla:***@localhost:15432/wasla_db' \
MON_DB_URL='postgresql+psycopg2://ivan:***@localhost:15433/main-ste' \
.venv/bin/uvicorn app.main:app --port 8000

# In another terminal: live mode (reads the API, WS live tick on Overview)
cd analytics_dashboard
pnpm dev                              # http://localhost:3000
```

API docs at http://localhost:8000/docs. The live feed degrades to `live:false`
instead of crashing when the tunnels go down.

### 5. Docker demo (optional)

```bash
export JEM_DB_URL='postgresql+psycopg2://wasla:***@host.docker.internal:15432/wasla_db'
export MON_DB_URL='postgresql+psycopg2://ivan:***@host.docker.internal:15433/main-ste'
docker compose up --build             # dashboard on :3001, API on :8000
docker compose down                   # clean up
```

## Tests

```bash
cd analytics_dashboard && pnpm test && pnpm lint && pnpm build
cd ../analytics_api && .venv/bin/python -m pytest -q
```

## Reports & docs

- `FINAL_REPORT.md` — full technical report with all metrics
- `report/report.tex` → `report/report.pdf` — internship report (LaTeX)
- `INTERNSHIP_KNOWLEDGE.md` / `HANDOVER_GUIDE.md` — project context and gotchas
- `Phase_2/STATS_REPORT.md`, `Phase_3/FORECAST_REPORT.md` — per-phase deliverables

## Rules

- Production databases are accessed **read-only**; the API never writes.
- Large regenerable artifacts are kept out of git (see `Phase_1/NOTES.md` §8).
