"""Phase 3 - Forecasting & Anomaly Detection configuration."""

from pathlib import Path

BASE = Path(__file__).resolve().parent
P2 = BASE.parent / "Phase_2"
P1 = BASE.parent / "Phase_1"
CLEAN = P1 / "data" / "clean"
FEAT = P1 / "data" / "features"

CHARTS = BASE / "charts"
OUT = BASE / "output"
MODELS = BASE / "models"
for d in (CHARTS, OUT, MODELS):
    d.mkdir(parents=True, exist_ok=True)

STATIONS = ["jemmal", "monastir"]

# Forecasting settings
FORECAST_HORIZON = 7          # days
HOLDOUT_DAYS = 7              # held out for walk-forward eval
SEASONAL_PERIOD = 7           # daily bookings have weekly seasonality
