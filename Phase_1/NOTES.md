# Phase 1 — Operational Notes

How the extraction was actually done, and gotchas learned along the way.

## 1. SSH tunnels (must be open before running 01_extract.py)

```
# Jemmal (jammel-server)
ssh -fN -L 15432:localhost:5432 server@100.72.205.59

# Monastir
ssh -fN -L 15433:localhost:5432 ste@100.123.86.114
```
SSH keys/credentials used: `server@100.72.205.59` (key auth), `ste@100.123.86.114` (password `ste2025`, via sshpass).

The local psql ports 15432/15433 forward to each server's localhost:5432. `config.py` points at these ports.

Check: `pg_isready -h localhost -p 15432` / `pg_isready -h localhost -p 15433`.

## 2. DB connection

- Host: localhost (via tunnel), DB `wasla_db`, user `wasla`, password `Lost2409`.
- `01_extract.py` accepts `DB_HOST`/`DB_PORT` env overrides per station:
  ```bash
  DB_PORT=15433 python3 01_extract.py --station monastir
  DB_PORT=15432 python3 01_extract.py --station jemmal
  ```

## 3. Extraction gotchas

- Monastir `bookings` is ~1M rows, 32 cols; `print_jobs` ~500k rows. Extracting over the tunnel with pandas took ~20–25 min total for Monastir (2 chunks of ~5 min each plus 1M-row transfer). Jemmal finished in ~2 min.
- No pagination needed in practice; streaming cursor avoided memory blow-up on the 1M-row table.
- Rows were fetched in `id`-ordered batches to keep memory bounded (see `fetch_in_batches` in 01_extract.py).
- Empty/transient tables are handled gracefully (skip + log).

## 4. Schema differences between stations

`bookings` differs between the two DBs:
- Monastir-only cols: `sub_route`, `sub_route_name`, `payment_processed_at`, `created_offline`, `local_id`, `created_by_name`, `user_ref`, `expires_at`.
- `02_clean.py` unions columns (outer join), so Monastir-only cols are NaN for Jemmal rows.

## 5. Data quirks worth remembering

- **Ghost bookings dominate**: 96.9% of bookings have `is_ghost_booking=true` and `is_verified=false`. Treat `is_ghost=false` as the "real sold ticket" set (~37k rows) when doing revenue/demand analytics; ghost rows are pre-generated/offline drafts.
- `created_by` is a user id; `created_by_name` only exists on Monastir.
- Cancellation data is essentially absent (115 cancelled out of 1.19M; only 7 with a reason).
- All payment_method = CASH; `payment_processed_at` (Monastir) is largely the proxy for actual sale time — verify before using in forecasts.
- `routes` tables differ in column count between stations (12 vs 11 cols); union in clean layer handles it.

## 6. Environment

- Python 3.12 via mise, pandas 2.3.3, pyarrow, matplotlib, sqlalchemy, psycopg2-binary.
- No virtualenv used; system python has everything. If you create one:
  ```bash
  python3 -m venv .venv && source .venv/bin/activate && pip install pandas pyarrow sqlalchemy psycopg2-binary matplotlib
  ```

## 7. Next steps (Phase 2)

- Forecast hourly/daily demand per route from `demand_hourly` / `demand_daily` (seasonality by hour + weekday).
- Use `route_performance` to size vehicles per destination; `print_jobs` can show ticket-print throughput.
- Evaluate whether to drop ghost bookings for training, or model them separately (draft vs sold).

## 8. Files excluded from git (GitHub 100 MB limit)

Raw CSVs are committed as `.csv.gz` (compressed 5–10x). The following large,
regenerable artifacts stay out of git and are excluded via `.gitignore`:

- `data/raw/*.csv` — regenerate: `python3 scripts/01_extract.py <station>` then `gzip -9`
- `data/raw/monastir_print_jobs.parquet` — same (135 MB)
- `data/clean/print_jobs.parquet` (153 MB), `data/clean/bookings.parquet` (118 MB) — regenerate: `python3 02_clean.py`
- `data/features/bookings_enriched.parquet` (124 MB) — regenerate: `python3 03_features.py`
