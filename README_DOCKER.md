# Local demo (docker compose)

```bash
# optional, for the live feed: SSH tunnels on the host + DB URLs
export JEM_DB_URL='postgresql+psycopg2://wasla:***@host.docker.internal:15432/wasla_db'
export MON_DB_URL='postgresql+psycopg2://ivan:***@host.docker.internal:15433/main-ste'

docker compose up --build
```

- Dashboard: http://localhost:3001 (API mode, reads http://localhost:8000)
- API docs: http://localhost:8000/docs

Without the DB env vars the live feed reports `live:false` — the rest keeps
working from the mounted artifacts. `docker compose down` removes everything;
nothing is ever written to production.

Mock-only variant (no API needed):
`NEXT_PUBLIC_USE_MOCK=1 docker compose build dashboard` then browse — the
dashboard serves its own committed mock JSON.
