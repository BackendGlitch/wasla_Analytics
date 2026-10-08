# Design Spec — Phases 4 & 5: Analytics Dashboard + API + Live Feed + Docker

**Date:** 2026-10-08
**Status:** Approved (user sign-off 2026-10-08)
**Scope:** Phase 4 (Next.js dashboard) and Phase 5 (FastAPI + WebSocket + Docker). Phase 6 (final report) happens after, same day, and is summarized at the end.
**Inputs:** `HANDOVER_GUIDE.md`, `INTERNSHIP_KNOWLEDGE.md`, `Phase_1/NOTES.md`, Phase 2/3 reports.

## Decisions locked with the user

| Decision | Choice |
|---|---|
| Data freshness | Re-extract fresh data from live stations (tunnels up; both extractions running in background at spec time) |
| UI style | Distinctive dark ops-dashboard theme (not ERP-clone) |
| Fleet view | Included (7 views total), labeled "indicative" |
| Build sequence | Mock-first: TS API shapes → dashboard on mocks → FastAPI matching shapes → flip toggle → WS + Docker |

## 1. Architecture

Three standalone pieces, all inside the existing `Internship/` git repo (not a monorepo — each has its own package manifest):

```
Internship/
  analytics_dashboard/   Next.js 16 (App Router) + TypeScript + Tailwind v4 + Recharts 3, pnpm
  analytics_api/         FastAPI + uvicorn, in-memory parquet cache, REST + WebSocket, Docker
  docker-compose.yml     api on 8000, dashboard on 3001, Phase_* artifacts mounted read-only
  FINAL_REPORT.md        Phase 6 deliverable (written tonight after 4+5 are demo-able)
```

The API contract is the linchpin of mock-first: JSON shapes are defined once as TypeScript types (`analytics_dashboard/lib/types.ts`) and both the mock JSON files and the FastAPI responses conform to them.

## 2. Data pipeline prerequisite (runs while we build)

Extraction (already running in background) → re-run `Phase_1/02_clean.py` → `03_features.py` → `04_eda.py` → all of Phase 2 → all of Phase 3, so every artifact the dashboard/API read is fresh (data through ~2026-10-08 instead of 2026-08-12). Then `analytics_dashboard/scripts/gen_mocks.py` regenerates mock JSON from the fresh artifacts.

## 3. API contract

### 3.1 REST endpoints (all GET unless noted; JSON; shapes mirrored by dashboard mocks)

- `GET /api/overview` — KPI cards. Per station + totals: latest-full-day bookings, revenue with **both** definitions labeled (`revenue_passenger_paid`, `revenue_station_fee`), real vs ghost counts, active vehicles, trips. `anomaly_today` (consensus flag for latest day) or null. `data_through` date. "Today" from cached artifacts means *latest full day in dataset* — the live WS tick is what carries real-time today numbers; the UI labels the date explicitly.
- `GET /api/flow/hourly` — `demand_hourly.parquet`: station, hour, bookings, seats, station-fee revenue.
- `GET /api/flow/daily` — `demand_daily.parquet`: station, date, bookings, real, ghost, both revenues.
- `GET /api/revenue` — daily revenue series, real-vs-ghost daily series, per-route breakdown (bookings, both revenues, avg ticket, ghost rate).
- `GET /api/routes` — `route_performance.parquet`, both stations side by side, grouped by the 5-route `group` mapping from `Phase_1/config.py`.
- `GET /api/fleet` — avg load factor, capacity coverage %, active vehicles, trips/vehicle, daily load-factor series, plus `caveat: "indicative — Monastir capacity present on ~33% of trips"`.
- `GET /api/forecast` — reads `Phase_3/models/model_meta_*.json`: per-station + total model name, CV MAPE, horizon, 7-day forecast with lo/hi, plus last-2-weeks predicted-vs-actual from `Phase_3/output/forecast_*.parquet` + `series_*.parquet`.
- `GET /api/anomalies` — from `Phase_3/output/anomaly_summary.json`: date, station, bookings, detectors fired, zero-day marker, consensus flag.
- `GET /api/health` — status, cache loaded-at, artifacts path, per-station tunnel status.
- `POST /api/refresh` — reload parquet cache in place, 204. (Cache-busting without restart.)

### 3.2 WebSocket

- `WS /ws/live` — tick every 60s: `{type:"tick", at, live, stations:{jemmal:{bookings_today, revenue_passenger_paid, real, ghost, anomaly_flag}, monastir:{...}}, last_seen}`.
- Live numbers come from lightweight `count(*)`/`sum(...)` queries over the tunnels (ports 15432/15433) — never the 25-min extraction.
- Tunnels down → broadcast `live: false` + `last_seen` timestamp; never crash, never reconnect-storm. Per-station try/except.

### 3.3 Error handling

- Artifacts missing at API startup → `/api/health` reports `status: "degraded"` with a clear message; data endpoints return 503 with detail.
- Dashboard: per-view loading/empty/error states; API unreachable → error banner suggesting mock mode (`NEXT_PUBLIC_USE_MOCK=1`).
- Read-only discipline: API only issues SELECTs; DB creds in `.env` (gitignored); `.env.example` committed with placeholders. No secrets in commits.

## 4. Dashboard — 7 views, dark theme

Routes: `/` Overview · `/flow` Passenger Flow · `/revenue` Revenue · `/routes` Routes · `/fleet` Fleet · `/forecast` Forecast · `/anomalies` Anomalies. Shared Shell (sidebar nav + header with live-status chip and mock/API mode indicator).

- Data layer: `lib/api.ts`, one function per view. `NEXT_PUBLIC_USE_MOCK=1` → fetch committed static JSON from `mock/`; else `NEXT_PUBLIC_API_BASE` (default `http://localhost:8000`).
- Overview additionally subscribes to `/ws/live` (API mode only) and updates its today-cards.
- Every view renders a small `Source: <file>` caption (e.g. `Source: Phase_1/data/features/demand_hourly.parquet`) — satisfies the traceability acceptance criterion and reads well in report screenshots.
- Revenue view: dual-definition chart (passenger-paid vs station-fee) with explicit labels; real-vs-ghost chart reproducing Phase 2's `revenue_real_vs_ghost.png`.
- Forecast view: 7-day bands from model_meta lo/hi + predicted-vs-actual 2-week line + ghost-volume disclaimer.
- Dark theme: custom design tokens (background/surface/accent/status colors), Recharts dark-styled; distinctive but restrained (per `frontend-design` skill guidance at build time). English UI labels; Arabic destination names kept as-is from the data.

## 5. API internals

```
analytics_api/
  app/main.py            # FastAPI, CORS for localhost:3001, routers, /api/health, /api/refresh
  app/cache.py           # loads parquet/JSON artifacts into memory at startup (MBs, fine); reload()
  app/live.py            # 60s poll thread (lightweight queries) + WebSocket broadcaster
  tests/test_api.py      # pytest smoke: shapes + a couple of numbers vs recomputed parquet sums
  requirements.txt
  Dockerfile             # python:3.12-slim, uvicorn
  docker-entrypoint.sh
  .env.example           # DB creds / artifact path placeholders
  README.md
```

- Artifact locations: `../Phase_1/data/features/`, `../Phase_2/output/`, `../Phase_3/models/`, `../Phase_3/output/` — overridable via `ARTIFACTS_DIR` env.
- Live query config via env (`JEM_DB_URL`, `MON_DB_URL`); if unset, live feed starts in `live:false` mode.

## 6. Docker + local demo

- `analytics_api/Dockerfile`, `analytics_dashboard/Dockerfile` (build args: `NEXT_PUBLIC_API_BASE`, `NEXT_PUBLIC_USE_MOCK`).
- `Internship/docker-compose.yml`: `api` (8000) mounts `../Phase_1 ../Phase_2 ../Phase_3` read-only; `dashboard` (3001) built with `NEXT_PUBLIC_API_BASE=http://localhost:8000`, `NEXT_PUBLIC_USE_MOCK=0`. No hardcoded IPs; env-driven so the same file can move to a VPS later.
- README at compose level: `docker compose up --build`, open `localhost:3001`, how to switch mock mode.
- `docker compose down` cleans up; API never writes to prod.

## 7. Testing & verification (evidence-based, matching the project's culture)

1. `analytics_dashboard/scripts/verify_mocks.py` — independently re-sums parquet/JSON artifacts and diffs against `mock/*.json`. Run after every mock regeneration.
2. API: `pytest tests/` + curl checks (`/api/overview` numbers equal hand-computed parquet sums).
3. E2E: `docker compose up --build` → browse all 7 views → kill tunnels → Overview shows `live:false` gracefully.
4. Dashboard: `pnpm lint` and `pnpm build` clean.

## 8. Acceptance criteria (Phase 4+5 "done")

- All 7 views render; every KPI traceable to a parquet/JSON file (Source captions + verify_mocks passing).
- Mock ⇄ API toggle works.
- `/api/overview` via curl returns numbers matching parquet ground truth.
- WS tick updates Overview cards; tunnels down → `live:false`, API stays up.
- `docker compose up --build` works from a clean checkout; `docker compose down` cleans up.
- `pnpm lint` / `pnpm build` clean; `pytest` passes.

## 9. Phase 6 (same evening, after 4+5)

`FINAL_REPORT.md` at `Internship/` root, following HANDOVER_GUIDE §6: executive summary (1 page + chart), data, methodology (walk-forward CV, SARIMA/seasonal-naive winners, Prophet rejection, 3-detector consensus), results (fresh metrics from tonight's re-run), limitations (ghost dominance, short Jemmal history, sparse fleet data, partial extraction day, tunnels laptop-bound), recommendations (06h/12h capacity, ghost-rate drift monitoring, real-only revenue forecasts, seasonality after a full quarter), appendix (how to run, file map). Includes screenshots from the live dashboard. Lead with the two headline findings: ghost bookings (~97%) and the dual-revenue gap.

## 10. Explicitly out of scope

- VPS/cloud deployment (local demo only, per current decision — compose file merely designed to move later).
- ERP integration, Nginx, auth.
- Cancellation analytics (data essentially absent).
- Prophet in production paths (kept in Phase_3 code but not built around).
- Writing to production DBs, ever.
