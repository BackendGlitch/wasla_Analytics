# Phase 1 — Data Extraction & EDA

Unified dataset from both Wasla stations (Jemmal + Monastir) for capacity/demand analytics.

## Pipeline

| Step | Script | Output |
|---|---|---|
| Extract | `scripts/01_extract.py` | `data/raw/{station}_{table}.parquet` |
| Clean / unify | `02_clean.py` | `data/clean/{table}.parquet` |
| Features | `03_features.py` | `data/features/*.parquet` |
| EDA | `04_eda.py` | `data/eda/*.png` + `data/eda/SUMMARY.md` |

Run the pipeline (needs SSH tunnels open — see NOTES.md):
```bash
python3 scripts/01_extract.py jemmal
python3 scripts/01_extract.py monastir
python3 02_clean.py
python3 03_features.py
python3 04_eda.py
```

## Data sources

| Station | DB | Tunnel |
|---|---|---|
| Jemmal | `jammel-server` (`server@100.72.205.59`) | localhost:15432 |
| Monastir | `ste@100.123.86.114` | localhost:15433 |

DB: `wasla_db`, user `wasla`, password `Lost2409` (prod) / `test` (dev).

## Tables extracted (8 per station)

`bookings`, `trips`, `print_jobs`, `day_passes`, `staff_transaction_log`, `routes`, `staff`, `vehicles`

## Data volumes (clean layer)

| Table | Rows |
|---|---|
| bookings | 1,188,298 |
| print_jobs | 511,173 |
| staff_transaction_log | 163,978 |
| day_passes | 30,808 |
| trips | 4,992 |
| routes | 9 |
| staff | 40 |
| vehicles | 305 |

Date range: 2025-10-13 → 2026-08-12.

## Key EDA findings

- Monastir = 87% of bookings (1.04M vs 150k).
- 96.9% of bookings are marked `is_ghost_booking = true` (pre-generated draft rows, `is_verified = false`); only 37k (3.1%) are real sold tickets.
- Peak demand: Jemmal ~06–08h, Monastir ~11–13h.
- Cancellations are nearly absent (0.01%) — `cancellation_reason` only populated on 7 rows.
- All payments are `CASH`; average revenue 2.10 TND/booking (2.03 ghost, 4.44 real).
- See `data/eda/SUMMARY.md` + charts for full detail.

## Directory layout

```
Phase_1/
  config.py            # DB endpoints (tunnel ports), station metadata, DESTINATION_MAP
  scripts/
    01_extract.py      # pull raw tables -> data/raw
  02_clean.py          # unify schemas, add station col, timestamp dtypes
  03_features.py       # enrich bookings + demand aggregates + unified destinations
  04_eda.py            # charts + summary report
  data/
    raw/               # per-station parquet extracts (16 files)
    clean/             # unified tables (1 file per table)
    features/          # bookings_enriched, demand_hourly, demand_daily, route_performance
    eda/               # PNG charts + SUMMARY.md
  logs/                # extraction logs
```
