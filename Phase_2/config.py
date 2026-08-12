"""Phase 2 - Statistical Analysis configuration.

Points at the Phase_1 clean/features layers (single source of truth) and
defines output paths + shared constants (revenue conventions, ghost split).
"""

from pathlib import Path

BASE = Path(__file__).resolve().parent
P1 = BASE.parent / "Phase_1"
CLEAN = P1 / "data" / "clean"
FEAT = P1 / "data" / "features"

CHARTS = BASE / "charts"
OUT = BASE / "output"
for d in (CHARTS, OUT):
    d.mkdir(parents=True, exist_ok=True)

STATIONS = ["jemmal", "monastir"]

# Revenue conventions (see INTERNSHIP_KNOWLEDGE.md 6.1)
#  - passenger-paid: SUM(total_amount) from bookings (base + service fee)
#  - station commission: seats x routes.service_fee (default 0.15 TND/seat)
STATION_FEE_PER_SEAT = 0.15
DAY_PASS_PRICE = 2.0

GHOST_NOTE = (
    "ghost bookings are pre-generated/offline drafts (is_verified=false). "
    "'Real' = is_ghost=false."
)
