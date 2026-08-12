# Wasla Analytics Internship — Handover Guide (Phases 4, 5, 6)

**Who this is for:** Yasmine (or whoever continues this internship).
**Who wrote it:** the person who built Phases 1–3. Read this whole file once before you write any code.
**Companion docs (read these too):**
- `INTERNSHIP_KNOWLEDGE.md` — the project brief, the pipeline, the tech stack, and — importantly — §6 "Technical Gotchas" where reality disagrees with the brief. Everything here assumes you've read that.
- `Phase_1/NOTES.md` — how the data was extracted, credentials, gotchas.
- `Phase_1/README.md`, `Phase_2/STATS_REPORT.md`, `Phase_3/FORECAST_REPORT.md` — what each phase produced.

This file has two big jobs:
1. Tell you exactly what's already done so you don't redo it (or worse, redo it wrong).
2. Spell out what Phases 4, 5, 6 should look like, in enough detail that you can build them on your own.

If something here disagrees with `INTERNSHIP_KNOWLEDGE.md`, trust the knowledge file for *business* context, but trust the code/data on disk for *what's actually true* — the brief describes the system a bit too nicely in places (we found that out the hard way).

---

## 0. One-paragraph summary

We pull production data from two live station databases (Jemmal and Monastir), clean it into one unified dataset, run statistical analysis, and build forecasting + anomaly detection on it. Phases 1 (extract/clean), 2 (stats), and 3 (forecast + anomalies) are **done and verified**. What's left is **Phase 4: a Next.js dashboard**, **Phase 5: a FastAPI layer + Docker + a live WebSocket feed**, and **Phase 6: the final report**. The intern owns 4, 5, 6. This doc is the map.

---

## 1. Where everything lives

```
Internship/
  INTERNSHIP_KNOWLEDGE.md        <- brief, pipeline, gotchas (read first)
  document.pdf / document1.pdf   <- original brief + signed training plan
  HANDOVER_GUIDE.md              <- this file

  Phase_1/                       <- DONE: extraction + cleaning
    config.py                    <- DB endpoints (via SSH tunnels), table list, DESTINATION_MAP
    scripts/01_extract.py        <- pull raw tables -> data/raw/ (needs tunnels open)
    02_clean.py                  <- unify both stations -> data/clean/ (8 tables)
    03_features.py               <- enrich bookings + demand aggregates -> data/features/
    04_eda.py                    <- charts + SUMMARY.md -> data/eda/
    README.md  NOTES.md
    data/
      raw/       16 parquet files (8 tables x 2 stations)
      clean/     8 unified tables (both stations merged)
      features/  bookings_enriched, demand_hourly, demand_daily, route_performance
      eda/       PNG charts + SUMMARY.md

  Phase_2/                       <- DONE: statistical analysis
    01_flow.py   02_revenue.py   03_routes.py   04_fleet.py   05_report.py
    STATS_REPORT.md              <- the "analysis deliverable" for your report
    charts/   output/*.json      <- numbers behind the report

  Phase_3/                       <- DONE: forecasting + anomaly detection
    01_prep.py   02_models.py   03_forecast.py   04_anomalies.py   05_report.py
    FORECAST_REPORT.md           <- the "model deliverable"
    models/model_meta_*.json     <- forecasts persisted for the dashboard to read
    output/                      <- series, CV folds, forecast/anomaly parquet + json summaries
    charts/
```

Phase 4 → create `Internship/analytics_dashboard/`.
Phase 5 → create `Internship/analytics_api/`.
Phase 6 → a report; where you put it is up to you (probably `Internship/FINAL_REPORT.md`).

---

## 2. What Phases 1–3 actually did (and the honest truth about it)

### Phase 1 — data
- Connected to two production Postgres DBs **through SSH tunnels** (read-only. Never write to production. The passwords are in `config.py`/`NOTES.md`).
- Extracted 8 tables per station to parquet (`bookings`, `trips`, `print_jobs`, `day_passes`, `staff_transaction_log`, `routes`, `staff`, `vehicles`).
- Unified both stations into a clean layer. **The stations have different column layouts** — e.g. bookings differ by 8 columns, trips use `booked_seats` vs `seats_booked` depending on station. The clean/features scripts handle this; if you touch them, re-check.
- Built a destination mapping (`DESTINATION_MAP` in `Phase_1/config.py`) because Jemmal IDs start `st_*` and Monastir start `station-*`. This is what makes the "5 routes" comparison possible.

Numbers (as of extraction 2026-08-12): **1,188,298 bookings** total; Monastir ~1.04M (87%), Jemmal ~150k. Date range Oct 2025 → Aug 2026 (Jemmal only starts Jun 2026).

### Phase 2 — statistics
- Passenger flow: **Jemmal peaks 06h, Monastir peaks 12h**, both ~3.3x off-peak. Morning/midday rush.
- Revenue — **this is the big one, read it twice:**
  - *Definition A "passenger-paid"* = `SUM(total_amount)` = what passengers pay (base fare + service fee). **~2.5M TND** consolidated.
  - *Definition B "station fee"* = seats × 0.15 TND + day passes × 2 TND = what the station actually keeps. **~179k TND**.
  - The gap is real and intentional: base fare goes to the driver. **Always state which "revenue" you're reporting** or the numbers look broken.
- **Ghost bookings:** ~97% of all bookings have `is_ghost_booking=true` (pre-generated drafts / offline, `is_verified=false`). **"Real" = `is_ghost=false`** (only ~37k rows). This decision ripples through everything you build. Don't model "revenue" on ghosts.
- Routes: Jemmal→Tunis is the money route (16.30 TND avg ticket, only 1.7% ghosts). Monastir routes are ~100% ghost, so Monastir "revenue" is not meaningful yet.
- Fleet: average load factor ~90%+ (near-full dispatch). But Monastir only has `vehicle_capacity` on **33%** of trips → fleet numbers there are indicative only.
- Cancellations: effectively zero (0.005%). Don't build cancellation analytics; there's no data.

### Phase 3 — forecasting + anomalies
- Built **daily time series** per station + total, continuous calendar index (missing days → 0).
- Validated models with **walk-forward CV** (4 expanding-window folds, predicting next 7 days each) — this is robust, a single holdout split would have lied to you.
  - Jemmal → **naive** (MAPE 9.1% ± 2.2%)
  - Monastir → **seasonal naive** (MAPE 10.3% ± 5.0%)
  - Total → **SARIMA** (MAPE 9.2% ± 3.7%)
  - Prophet was consistently worse (over-parametrised for short history). We kept the code so you can re-run, but don't build around it.
- 7-day forecasts persisted to `models/model_meta_*.json` — **this is what the dashboard's Forecast view should read**.
- Anomaly detection: 3 detectors (rolling z, week-over-week differencing z, IsolationForest) + consensus. Found real flags: Jemmal 2026-06-29 spike; Monastir zero-booking days 2026-01-20 and 2026-05-27 (a plain z-score missed these — that's why there are 3 detectors).

### Honest caveats to keep in front of you
1. Ghost/draft bookings dominate volume. **Forecast volume on all bookings, forecast revenue on real only.** Mixing them distorts revenue ~10–15x.
2. Only ~2 months of Jemmal history. Month-of-year seasonality is unmeasured. Keep the forecast horizon at 7 days (or 14 max) until more data exists.
3. The **extraction day is partial** (we extracted at 04:09, so that day had 16 bookings). `Phase_3/01_prep.py` drops such a trailing day automatically. If you re-extract and see absurdly low "today" numbers, that's why.
4. Tunnels only exist while this machine is on. Live/near-real-time data works locally but nothing reaches the dashboard if the tunnels die. (This is why Phase 5's "live" feed is a **lightweight** query, not a re-extraction.)

---

## 3. How to run everything (so you can verify before building)

Tunnels (Phase 3/5 need them; Phase 1 extraction too):
```bash
ssh -fN -L 15432:localhost:5432 server@100.72.205.59   # Jemmal
ssh -fN -L 15433:localhost:5432 ste@100.123.86.114      # Monastir
```
(Key auth for server@…, password `ste2025` via sshpass for ste@… — see `Phase_1/NOTES.md`.)

Re-run any phase's pipeline (order matters):
```bash
cd Internship/Phase_1 && python3 scripts/01_extract.py jemmal && python3 scripts/01_extract.py monastir  # ~25 min for monastir over the tunnel
python3 02_clean.py && python3 03_features.py && python3 04_eda.py
cd ../Phase_2 && python3 01_flow.py && python3 02_revenue.py && python3 03_routes.py && python3 04_fleet.py && python3 05_report.py
cd ../Phase_3 && python3 01_prep.py && python3 02_models.py && python3 03_forecast.py && python3 04_anomalies.py && python3 05_report.py
```

Python setup: **no venv exists** (someone kept meaning to make one and never did). The system `python3` (3.12 via mise) has: pandas 2.3.3, numpy, scipy, statsmodels 0.14.6, prophet 1.3.0, scikit-learn 1.8.0, matplotlib, seaborn, pyarrow, sqlalchemy, psycopg2-binary. If you want a clean venv:
```bash
python3 -m venv .venv && source .venv/bin/activate && pip install pandas numpy scipy statsmodels prophet scikit-learn matplotlib seaborn pyarrow sqlalchemy psycopg2-binary
```

**Verify your work the way we did:** don't just eyeball charts. Recompute a number independently (e.g. sum the parquet yourself and compare to the reported figure). We caught real bugs this way — e.g. a partial day skewing MAPE to 3000%, and a wrong bar-chart x-position.

---

## 4. Phase 4 — the dashboard (your first big task)

**Goal:** a working operations dashboard for the two stations.
**Ownership (from the brief §6.5):** the existing ERP dashboard (`erp/`, admin.dhraief.live) owns *live operations BI*. **You own analytics: forecasting + anomaly detection + the analytics dataset.** Don't duplicate ERP's realtime ops screens; build on the forecast/analytics view. Say this explicitly when presenting.

### 4.1 Stack
- **Next.js (App Router)** + TypeScript + Tailwind.
- **Recharts** for charts (the ERP frontend already uses it — look at `erp/frontend/src/app/(app)/` for conventions, e.g. `analytics/`, `fleet/`, `stations/`).
- shadcn-style components if you like; `wasla-queue/` has them if you want to copy patterns.
- Create it at `Internship/analytics_dashboard/` with `pnpm create next-app` (or `npx create-next-app`). It gets its own package.json — this repo is *not* a monorepo, each project stands alone.

### 4.2 Data source for the UI
Fetch JSON from the Phase 5 API (`http://localhost:8000/api/...`). To keep the UI developable **before** the API exists, also ship a **mock/static mode**: point the data layer at the local artifact files (`Phase_3/models/model_meta_*.json`, `Phase_3/output/*.json`, `Phase_1/data/features/*.parquet`) and render identical shapes. Plan the API response shapes first, then make both the mock and the real fetch conform. This will save you days.

Suggest a small `lib/api.ts` with one function per view and a flag (env `NEXT_PUBLIC_USE_MOCK=1`). Internally it either returns the mock JSON or calls `/api/...`.

### 4.3 Views and what each shows (from the brief §3.4, trimmed to your ownership)
1. **Overview** — KPI cards: today's bookings, today's revenue (label it: passenger-paid vs station fee), real vs ghost split, current anomaly count. A note/banner if a consensus anomaly fired today.
2. **Passenger Flow** — hourly curve (overlay both stations — expect Jemmal peak ~06h, Monastir ~12h), daily trend line. Source: `Phase_1/data/features/demand_hourly.parquet`, `demand_daily.parquet` (or the API exposing them).
3. **Revenue** — daily revenue trend + per-route breakdown. **Label which definition.** The dual-definition chart (`revenue_real_vs_ghost.png` in Phase_2) is a good visual to reproduce.
4. **Routes** — the 5-route table (bookings, revenue, avg ticket, ghost rate). Source: `data/features/route_performance.parquet`. Include both stations side by side.
5. **Forecast** — the **7-day forecast with confidence bands** read from `Phase_3/models/model_meta_*.json` (already has model name, horizons, forecast, lo/hi). Show predicted-vs-actual for the last 2 weeks too (`Phase_3/output/forecast_*.parquet` + `series_*.parquet`). Add a disclaimer that volume includes ghost/draft bookings.
6. **Anomalies** — consensus-flagged days list from `Phase_3/output/anomaly_summary.json` (date, bookings, which detectors fired, zero-day marker). Show the anomaly chart if you want.

### 4.4 Acceptance criteria (what "done" means)
- App runs locally with `pnpm dev`; no warnings that matter.
- Every KPI/view has a number you can trace back to a parquet/json file (trace it, don't trust it).
- Toggle between mock data and real API works.
- All 7 views render; 404 for any missing route is fixed.
- Run `pnpm lint` and `pnpm build` clean before you call it done.

---

## 5. Phase 5 — the API + Docker + live feed

**Goal:** a read-only analytics API that serves the Phase 1–3 artifacts, plus a minutely live "today" WebSocket feed, packaged with Docker for local demo.

### 5.1 The service
Create `Internship/analytics_api/` — FastAPI (uvicorn). Structure (keep it boring and obvious):
```
analytics_api/
  app/
    main.py            # FastAPI entrypoint, CORS, routers
    cache.py           # load parquet sets into memory at startup (they're MBs, fine)
    mocks.py           # (reuse dashboard mocks if you prefer the API to be self-contained)
    live.py            # tunnel query worker + WebSocket broadcaster
  requirements.txt
  docker-entrypoint.sh
  README.md
```

### 5.2 REST endpoints
Serviced from the in-memory parquet cache. Return JSON, keep the shapes aligned with what the dashboard's `lib/api.ts` expects:
```
GET /api/overview      KPI cards: today/trailing bookings, revenue (both definitions), real/ghost, anomalies
GET /api/flow/hourly   demand_hourly.parquet (station, hour, bookings, seats, revenue)
GET /api/flow/daily    demand_daily.parquet
GET /api/revenue       daily revenue + real-vs-ghost + per-route
GET /api/routes        route_performance.parquet
GET /api/fleet         (optional; sparse data, label it indicative)
GET /api/forecast      Phase_3/models/model_meta_*.json (+ last-2-weeks actuals)
GET /api/anomalies     Phase_3/output/anomaly_summary.json
GET /api/health        status, cache loaded at, tunnels alive/not
```
Add a tiny cache-busting strategy (e.g. reload parquet on a schedule or on `POST /api/refresh`) so tomorrow's data is picked up without a container restart.

### 5.3 Live WebSocket feed
- `WS /ws/live`, broadcasts a JSON tick every **minute** (or every few seconds if you want it to feel alive — brief says real-time-ish).
- Tick payload: per station — today's bookings, today's revenue (passenger-paid), real vs ghost counts, last known anomaly flag for today.
- **Important:** compute these with **lightweight `count(*)`/`sum()` queries** against the existing tunnels (`localhost:15432/15433`), NOT the 25-minute full extraction. If the tunnel is down, broadcast `live: false` + a last-seen timestamp instead of crashing. Graceful degradation is part of the job.
- When a ticket is created in production you won't see it instantly (it's a polling feed over a tunnel) — that's fine and expected for Phase 5. Note it.

### 5.4 Read-only discipline
- The API never writes to the production DBs. Only `SELECT`. The refresh job re-reads parquet / cheap counts, nothing more.
- Keep credentials out of git: put DB config in env vars / `.env` (gitignore it). The placeholders live in `Phase_1/config.py` and `NOTES.md`; don't copy secrets into committed files.

### 5.5 Docker + local demo
- `Dockerfile` for the API, one for the dashboard; `docker-compose.yml` wiring them (`api` on 8000, `dashboard` on 3001, CORS open for localhost).
- Local demo only (per the current decision). Include a `README.md` with: `docker compose up --build`, then open the dashboard, and how to point the dashboard at the API (env var).
- If the laptop isn't reachable later, the same compose file is the basis for VPS deployment — design it as if it might move (no hardcoded IPs, env-driven).

### 5.6 Acceptance criteria
- `curl localhost:8000/api/overview` returns real numbers matching the parquet.
- WebSocket tick works and updates the dashboard's Overview cards.
- `docker compose up --build` works on a clean machine; shutting down tunnels doesn't crash the API (it reports `live:false`).
- `docker compose down` cleans up; no data left half-written on prod.

---

## 6. Phase 6 — the final technical report

**Goal:** the document from §3.5/§5 deliverables: methodology, results, recommendations. It's the thing the supervisor (Mr. Samer Gassouma, CEO) will actually read, so make it readable by a non-DS person.

Suggested structure (adapt freely):
1. **Executive summary** — 1 page. What the system does, the 3 headline findings (ghost dominance, dual revenue, peaks/fleet load). Include one chart.
2. **Data** — sources, the two stations, extraction through tunnels, cleaning/unification, the destination mapping.
3. **Methodology** — forecasting: walk-forward CV, models tried, why SARIMA/seasonal-naive won, why Prophet didn't. Anomaly detection: 3 detectors + consensus + zero-day rule.
4. **Results** — the tables from `STATS_REPORT.md` + `FORECAST_REPORT.md` (MAPE/RMSE, forecasts with CI), the anomaly flags found and what they meant.
5. **Limitations & caveats** — ghost vs real, short Jemmal history, sparse Monastir fleet/capacity data, partial-day artifact, tunnels=laptop-bound for now.
6. **Recommendations** — capacity planning to the 06h/12h peaks, ghost-rate drift monitoring (sustained >98% = possible offline/auto-gen bug), revenue forecasts on real subset only, revisit seasonality after a full quarter.
7. **Appendix** — how to run everything; file map.

Include the actual metrics (they're in the two reports) and cite the chart files. The two-revenue gap (§2 above, ~7% station share) and the ghost-bookings reality are the two findings that will most surprise the reader — lead with them.

---

## 7. Order of work + a suggested rhythm

1. **Read** `INTERNSHIP_KNOWLEDGE.md`, then `Phase_1/NOTES.md`, then the two phase reports. (~half a day; don't skip, this is cheap insurance.)
2. **Reproduce** all three pipelines on your machine so you trust the data. Fix nothing yet unless it's broken.
3. **Phase 4 first**: mock-data dashboard. Decide the API response shapes up front (write them as TypeScript types), build all 7 views against mocks.
4. **Then Phase 5**: implement the API reading the same artifacts; flip the dashboard to real API; add WebSocket + Docker.
5. **Phase 6** last, when the dashboard is demo-able. Screenshots from the real dashboard make the report credible.
6. Keep a short log of what you changed (a few lines a day). The next person — maybe the supervisor, maybe another intern — will love you for it.

Rhythm advice, from someone who just lived it: get *something* rendering end-to-end early (mock dashboard + one API call), then polish. And whenever a number looks weird, `sum()` the parquet by hand before debugging the dashboard — the bug is often upstream.

---

## 8. Gotcha checklist (read before each phase)
- [ ] I'm stating *which* revenue definition I'm showing (passenger-paid vs station fee).
- [ ] I'm not mixing ghost + real bookings in revenue metrics (volume can be all bookings; revenue = real only).
- [ ] I know which station column fills which field (booked_seats vs seats_booked; st_* vs station-*).
- [ ] I remembered the extraction day was partial (that's why "today" looks tiny right after an extract).
- [ ] Tunnels are up before I say "live" (and my code handles them being down).
- [ ] No write access to production. Read-only. Ever.
- [ ] Credentials stay out of committed files.

Good luck. The data is yours now — make something the station operators actually want to open.