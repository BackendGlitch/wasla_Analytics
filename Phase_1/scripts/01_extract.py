"""
Phase 1 - Extract raw tables from a station DB (read-only).

Usage:
    python 01_extract.py <jemmal|monastir>

Pulls every table listed in config.TABLES and writes both CSV and parquet
to data/raw/{station}_{table}.{csv,parquet}.

READ-ONLY: uses SELECT ... ORDER BY created_at (or id as fallback) only.
"""

import sys
from pathlib import Path

import pandas as pd
import sqlalchemy as sa

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from config import DATABASES, TABLES, RAW_DIR

# Ordering column per table so extraction is deterministic.
ORDER_BY = {
    "bookings": "created_at",
    "trips": "created_at",
    "day_passes": "created_at",
    "routes": "updated_at",
    "vehicles": "id",
    "staff": "created_at",
    "print_jobs": "created_at",
    "staff_transaction_log": "created_at",
}


def main(station: str) -> None:
    if station not in DATABASES:
        sys.exit(f"Unknown station '{station}'. Use one of {list(DATABASES)}")

    cfg = DATABASES[station]
    url = sa.engine.URL.create(
        "postgresql+psycopg2",
        host=cfg["host"],
        port=cfg["port"],
        database=cfg["dbname"],
        username=cfg["user"],
        password=cfg["password"],
    )
    engine = sa.create_engine(url)

    with engine.connect() as conn:
        for table in TABLES:
            order_col = ORDER_BY.get(table, "id")
            try:
                df = pd.read_sql_query(
                    sa.text(f'SELECT * FROM {table} ORDER BY "{order_col}"'),
                    conn,
                )
            except Exception as e:  # noqa: BLE001 - report and continue
                print(f"  [!] {station}/{table}: {e}")
                continue
            out_csv = RAW_DIR / f"{station}_{table}.csv"
            out_pq = RAW_DIR / f"{station}_{table}.parquet"
            df.to_csv(out_csv, index=False)
            df.to_parquet(out_pq, index=False)
            print(f"  {station}/{table}: {len(df):>9,} rows -> {out_csv.name} / {out_pq.name}")

    engine.dispose()


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    main(sys.argv[1])
