"""
Phase 1 - Data Cleaning & Dataset Creation
Configuration: DB endpoints (via SSH tunnels), tables, and the unified
destination mapping between Jemmal (st_*) and Monastir (station-*) stations.
"""

from pathlib import Path

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent                 # Phase_1/
RAW_DIR = BASE_DIR / "data" / "raw"
PROC_DIR = BASE_DIR / "data" / "processed"
EDA_DIR = BASE_DIR / "data" / "eda"

for d in (RAW_DIR, PROC_DIR, EDA_DIR):
    d.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# Databases
#
# Access is done from THIS laptop through an SSH port-forward tunnel
# (see README.md "Access" section). Each tunnel maps the remote server's
# localhost:5432 to a local port on this machine.
#
#   ssh -fN -L 15432:localhost:5432 server@100.72.205.59   # Jemmal
#   ssh -fN -L 15433:localhost:5432 ste@100.123.86.114      # Monastir
#
# Read-only SELECT statements only. Never write to production.
# ---------------------------------------------------------------------------
DATABASES = {
    "jemmal": {
        "host": "127.0.0.1",
        "port": 15432,          # tunnel -> wasla_db on jemmal server
        "dbname": "wasla_db",
        "user": "wasla",
        "password": "Lost2409",
    },
    "monastir": {
        "host": "127.0.0.1",
        "port": 15433,          # tunnel -> main-ste on monastir server
        "dbname": "main-ste",
        "user": "ivan",
        "password": "Lost2409",
    },
}

# ---------------------------------------------------------------------------
# Tables to extract per station
# ---------------------------------------------------------------------------
TABLES = [
    "bookings",
    "trips",
    "day_passes",
    "routes",
    "vehicles",
    "staff",
    "print_jobs",
    "staff_transaction_log",
]

# ---------------------------------------------------------------------------
# Unified destination mapping
# ---------------------------------------------------------------------------
# Each station uses a different id namespace:
#   Jemmal   -> st_*  (far destinations served from Jemmal)
#   Monastir -> station-* (local towns served from Monastir)
# "canonical" is the English name used across both stations in the unified
# dataset. "group" groups them for the 5-route comparison in the brief.
# ---------------------------------------------------------------------------
DESTINATION_MAP = {
    # --- Jemmal (st_*) ---
    "st_monastir":        {"canonical": "Monastir",      "group": "Monastir"},
    "st_sousse":          {"canonical": "Sousse",        "group": "Sousse"},
    "st_ksar_hellal":     {"canonical": "Ksar Hlel",     "group": "Ksar Hlel"},
    "st_souassi":         {"canonical": "Souassi",       "group": "Souassi"},
    "st_maghreb_nabeul":  {"canonical": "Tunis",         "group": "Tunis"},
    # --- Monastir (station-*) ---
    "station-jemmal":     {"canonical": "Jemmal",        "group": "Jemmal"},
    "station-ksar-hlel":  {"canonical": "Ksar Hlel",     "group": "Ksar Hlel"},
    "station-moknin":     {"canonical": "Moknin",        "group": "Moknin"},
    "station-teboulba":   {"canonical": "Teboulba",      "group": "Teboulba"},
    "station-tunis":      {"canonical": "Tunis",         "group": "Tunis"},
    "station-monastir":   {"canonical": "Monastir",      "group": "Monastir"},
    "station-sousse":     {"canonical": "Sousse",        "group": "Sousse"},
    "station-souassi":    {"canonical": "Souassi",       "group": "Souassi"},
    "station-ksar-hellal": {"canonical": "Ksar Hlel",    "group": "Ksar Hlel"},
}

# Value found in the data but not in the mapping -> kept, flagged unknown.
UNKNOWN_DESTINATION = {"canonical": "Unknown", "group": "Unknown"}


def destination_lookup(dest_id: str | None) -> dict:
    """Return the mapping entry for a destination id (or the Unknown entry)."""
    if not dest_id:
        return dict(UNKNOWN_DESTINATION)
    return DESTINATION_MAP.get(dest_id, dict(UNKNOWN_DESTINATION))
