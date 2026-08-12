"""Phase 1 - Step 2: Clean + unify both stations into a single dataset.

Loads the raw parquet extracts (data/raw/), adds a `station` marker,
unifies column schemas across stations, normalises timestamp columns,
and writes a single clean dataset to data/clean/.

Run:  python3 02_clean.py
"""

from pathlib import Path
import pandas as pd

BASE = Path(__file__).resolve().parent
RAW = BASE / "data" / "raw"
CLEAN = BASE / "data" / "clean"
CLEAN.mkdir(parents=True, exist_ok=True)

STATIONS = ["jemmal", "monastir"]
TABLES = [
    "bookings",
    "trips",
    "print_jobs",
    "day_passes",
    "staff_transaction_log",
    "routes",
    "staff",
    "vehicles",
]

TS_COLUMNS = [
    "created_at",
    "updated_at",
    "start_time",
    "departed_at",
    "completed_at",
    "verified_at",
    "cancelled_at",
    "payment_processed_at",
    "purchase_date",
    "valid_from",
    "valid_until",
    "printed_at",
    "expires_at",
]


def load_station(station: str, table: str) -> pd.DataFrame:
    path = RAW / f"{station}_{table}.parquet"
    if not path.exists():
        return pd.DataFrame()
    df = pd.read_parquet(path)
    df.insert(0, "station", station)
    return df


def to_ts(series: pd.Series) -> pd.Series:
    """Convert a column to pandas datetime, errors to NaT."""
    if series.dtype == "object":
        # Postgres may return string timestamps / ints for some dtypes
        return pd.to_datetime(series, errors="coerce", utc=False)
    return pd.to_datetime(series, errors="coerce")


def clean_table(table: str) -> pd.DataFrame:
    frames = []
    for station in STATIONS:
        df = load_station(station, table)
        if df.empty:
            print(f"  [skip] {station}.{table}: no raw file")
            continue
        for col in TS_COLUMNS:
            if col in df.columns:
                df[col] = to_ts(df[col])
        frames.append(df)

    if not frames:
        return pd.DataFrame()

    df = pd.concat(frames, ignore_index=True, sort=False)

    # Add derived time features once (avoid recomputation)
    if "created_at" in df.columns and pd.api.types.is_datetime64_any_dtype(df["created_at"]):
        df["created_date"] = df["created_at"].dt.date
        df["created_hour"] = df["created_at"].dt.hour
        df["created_dow"] = df["created_at"].dt.dayofweek

    # sort by id then created_at for deterministic ordering
    if "id" in df.columns:
        df = df.sort_values(["id", "created_at"]).reset_index(drop=True)

    return df


def main() -> None:
    summary = {}
    for table in TABLES:
        print(f"Cleaning {table} ...")
        df = clean_table(table)
        if df.empty:
            print("  (no data)")
            continue
        out_path = CLEAN / f"{table}.parquet"
        df.to_parquet(out_path, index=False)
        summary[table] = len(df)
        print(f"  -> {len(df):>10,} rows x {len(df.columns)} cols  ({out_path.name})")

    print("\n=== CLEAN SUMMARY ===")
    for k, v in summary.items():
        print(f"  {k:<24} {v:>10,}")
    total = sum(summary.values())
    print(f"  {'TOTAL':<24} {total:>10,}")
    print(f"\nWritten to {CLEAN}")


if __name__ == "__main__":
    main()
