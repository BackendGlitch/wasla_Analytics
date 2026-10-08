"""Environment configuration for the analytics API.

Local dev resolves artifacts relative to this file (repo layout).
In Docker, ARTIFACTS_DIR points at the read-only mounted repo root.
Live-feed DB URLs are optional: when unset, the feed broadcasts live:false.
"""
import os
from pathlib import Path

# Default: parent of analytics_api/ = Internship/ (repo layout)
REPO = Path(os.environ.get("ARTIFACTS_DIR", str(Path(__file__).resolve().parent.parent.parent)))

FEAT = REPO / "Phase_1" / "data" / "features"
CLEAN = REPO / "Phase_1" / "data" / "clean"
P2_OUT = REPO / "Phase_2" / "output"
P3_MODELS = REPO / "Phase_3" / "models"
P3_OUT = REPO / "Phase_3" / "output"

JEM_DB_URL = os.environ.get("JEM_DB_URL")  # e.g. postgresql+psycopg2://wasla:***@localhost:15432/wasla_db
MON_DB_URL = os.environ.get("MON_DB_URL")  # e.g. postgresql+psycopg2://ivan:***@localhost:15433/main-ste

TICK_SECONDS = int(os.environ.get("TICK_SECONDS", "60"))

STATIONS = ["jemmal", "monastir"]
KEYS = ["jemmal", "monastir", "total"]
STATION_FEE_PER_SEAT = 0.15
