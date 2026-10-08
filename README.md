# Wasla Analytics — Transport Analytics & Operations Intelligence

Analytics layer on top of the live **Wasla** transport-management platform (Backend Glitch Inc.):
data extraction & cleaning from the two live stations, statistical analysis, demand forecasting,
anomaly detection, an operations dashboard, and a read-only analytics API with a live WebSocket feed.

**Intern:** Yasmine Ghomrassi — Master's in Statistics and Data Science, University of Palermo
**Supervisor:** Mr. Samer Gassouma (CEO, Backend Glitch Inc.) · **Location:** Monastir, Tunisia · **Period:** 1 July – 25 September 2026

## Live platform

🔗 **Dashboard on Vercel:** https://wasla-analytics-samers-projects-e0e34ea8.vercel.app

## The stack

```
Production Postgres (Jemmal + Monastir)
   └─ SSH tunnels (read-only) ─┐
Phase 1  extraction → clean → features (parquet)
Phase 2  statistics: flow, revenue (dual definition), routes, fleet
Phase 3  forecasting (walk-forward CV) + 3-detector anomaly consensus
Phase 4  Next.js dashboard — 7 views, dark theme, mock ⇄ live API modes
Phase 5  FastAPI — REST endpoints + WS /ws/live (60s live tick) + Docker compose
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

![Architecture](analytics_dashboard/docs/architecture.png)

## Quick start

```bash
# SSH tunnels to the station DBs (read-only) — see Phase_1/NOTES.md
# 1. Re-run the data pipeline
cd Phase_1 && python3 02_clean.py && python3 03_features.py && python3 04_eda.py
cd ../Phase_2 && for f in 01_flow 02_revenue 03_routes 04_fleet 05_report; do python3 $f.py; done
cd ../Phase_3 && for f in 01_prep 02_models 03_forecast 04_anomalies 05_report; do python3 $f.py; done

# 2. Dashboard (mock mode first, no API needed)
cd ../analytics_dashboard && python3 scripts/gen_mocks.py && NEXT_PUBLIC_USE_MOCK=1 pnpm dev

# 3. API + live mode
cd ../analytics_api && python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
JEM_DB_URL=... MON_DB_URL=... .venv/bin/uvicorn app.main:app --port 8000
cd ../analytics_dashboard && pnpm dev          # live mode, WS live tick on Overview

# 4. Docker demo
docker compose up --build                       # dashboard :3001, API :8000
```

## Reports & docs

- `FINAL_REPORT.md` — full technical report with all metrics
- `report/report.tex` — internship report (LaTeX)
- `INTERNSHIP_KNOWLEDGE.md` / `HANDOVER_GUIDE.md` — project context and gotchas
- `Phase_2/STATS_REPORT.md`, `Phase_3/FORECAST_REPORT.md` — per-phase deliverables

## Rules

- Production databases are accessed **read-only**; the API never writes.
- Large regenerable artifacts are kept out of git (see `Phase_1/NOTES.md` §8).
