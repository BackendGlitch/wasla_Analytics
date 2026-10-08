# Wasla Analytics API (Phase 5)

Read-only analytics API serving the Phase 1–3 artifacts + a minutely live feed.

## Run locally

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
JEM_DB_URL='postgresql+psycopg2://wasla:***@localhost:15432/wasla_db' \
MON_DB_URL='postgresql+psycopg2://ivan:***@localhost:15433/main-ste' \
.venv/bin/uvicorn app.main:app --port 8000
```

(Requires the SSH tunnels to be up; see `../Phase_1/NOTES.md`. Without the env
vars the API still serves cached artifacts and the live feed reports `live:false`.)

## Endpoints

| Endpoint | Content |
|---|---|
| `GET /api/overview` | KPIs, both revenue definitions, real/ghost split, latest-day anomaly flag |
| `GET /api/flow/hourly` `GET /api/flow/daily` | passenger flow |
| `GET /api/revenue` | daily dual-definition revenue + real-vs-ghost + per-route |
| `GET /api/routes` | route performance, both stations |
| `GET /api/fleet` | fleet summary (indicative) + daily trips |
| `GET /api/forecast` | 7-day forecasts + confidence bands + predicted-vs-actual |
| `GET /api/anomalies` | consensus-flagged days |
| `GET /api/health` | status, cache info, tunnel configuration |
| `POST /api/refresh` | reload artifact cache (204) |
| `WS /ws/live` | minutely live tick (bookings/revenue/real/ghost per station) |

## Rules

- READ-ONLY: the service only runs SELECT queries and reads parquet/JSON files.
- Credentials via env vars / `.env` (see `.env.example`) — never commit secrets.
- Live queries are lightweight aggregates, not the full extraction.
