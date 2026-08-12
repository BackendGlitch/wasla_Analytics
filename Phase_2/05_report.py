"""Phase 2 - Build the consolidated STATS_REPORT.md.

Reads output/*.json (produced by 01-04) and writes a single markdown
statistical-analysis report in Phase_2/.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from config import OUT, CHARTS, P1, STATION_FEE_PER_SEAT, DAY_PASS_PRICE


def j(path: str):
    with open(OUT / path) as f:
        return json.load(f)


def main() -> None:
    flow = j("flow_stats.json")
    rev = j("revenue_stats.json")
    routes = j("route_stats.json")
    fleet = j("fleet_stats.json")
    canc = j("cancellation_stats.json")

    L = []
    add = L.append
    add("# Phase 2 — Statistical Analysis Report")
    add("")
    add(f"Generated from the Phase_1 clean/features layers ({P1}).")
    add("")
    add("## 1. Passenger flow")
    add("")
    add("| Station | Total bookings | Real (sold) | Ghost rate | Avg/day | Peak hour | Peak/off-peak |")
    add("|---|---|---:|---:|---:|---:|---:|")
    for st in ["jemmal", "monastir"]:
        f = flow[st]
        add(
            f"| {st.capitalize()} | {f['total_bookings']:,} | {f['real_bookings']:,} | "
            f"{f['ghost_rate']:.1%} | {f['avg_bookings_per_day']:,.0f} | "
            f"{f['peak_hour']:02d}h | {f['peak_offpeak_ratio']:.2f}x |"
        )
    add("")
    add("- Jemmal peaks in the **morning (06h)**; Monastir in the **midday (12h)** rush.")
    add("- Ghost rate is ~3x higher at Monastir; treat flow analytics on the real subset separately.")
    add("")
    add("## 2. Revenue (dual definition)")
    add("")
    add(f"**Definition A (passenger-paid)** = SUM(`total_amount`) — base fare + service fee (what the passenger pays).")
    add(f"**Definition B (station fee)** = seats × {STATION_FEE_PER_SEAT} TND + day passes × {DAY_PASS_PRICE} TND — what the station keeps.")
    add("")
    add("| Station | Passenger-paid | Station fee (bookings) | Day-pass fee | Real-bookings rev |")
    add("|---|---:|---:|---:|---:|")
    for st in ["jemmal", "monastir"]:
        r = rev[st]
        add(
            f"| {st.capitalize()} | {r['passenger_paid_total']:,.0f} | {r['station_fee_bookings']:,.0f} | "
            f"{r['station_fee_day_passes']:,.0f} | {r['real_bookings_rev']:,.0f} |"
        )
    add("")
    c = rev["consolidated"]
    add(
        f"Consolidated: passenger-paid **{c['passenger_paid_total']:,.0f} TND** vs station fee "
        f"**{c['station_fee_total']:,.0f} TND** — the {c['station_fee_total']/c['passenger_paid_total']:.1%} "
        "share stays with the station; the rest goes to drivers. "
        "Real (sold) bookings contribute only a fraction of passenger-paid totals because ghosts dominate."
    )
    add("")
    add("## 3. Route performance")
    add("")
    add("| Station | Route | Bookings | Revenue (TND) | Avg ticket | Ghost rate |")
    add("|---|---|---:|---:|---:|---:|")
    for st in ["jemmal", "monastir"]:
        rs = routes[st]
        for dest, m in rs.items():
            if dest in ("busiest_month", "total_rt"):
                continue
            add(
                f"| {st.capitalize()} | {dest} | {m['bookings']:,} | {m['revenue']:,.0f} | "
                f"{m['avg_ticket']:.2f} | {m['ghost_rate']:.1%} |"
            )
    add("")
    add("- **Jemmal→Tunis** is the highest-value route: 4,349 bookings / 70,882 TND (16.30 TND avg, 1.7% ghosts).")
    add("- **Jemmal→Souassi** second-highest avg ticket (4.75 TND) with 58% ghosts.")
    add("- **Monastir** routes are almost entirely ghost (99.9%); real volume is negligible — likely drafts/offline.")
    add("")
    add("## 4. Fleet utilization")
    add("")
    add("| Station | Trips | Vehicles seen | Trips/vehicle | Avg load factor | Capacity coverage | Window |")
    add("|---|---:|---:|---:|---:|---:|---|")
    for st in ["jemmal", "monastir"]:
        f = fleet[st]
        cov = f"{f['load_factor_coverage']:.0%}" if f.get("load_factor_coverage") else "—"
        add(
            f"| {st.capitalize()} | {f['trips']:,} | {f['vehicles_seen']:,} | "
            f"{f['trips_per_vehicle']:.1f} | {f['avg_load_factor']:.1%} | {cov} | "
            f"{f['date_from'][:10]} → {f['date_to'][:10]} |"
        )
    add("")
    add("- Average **load factor ~90%+** at both stations — vehicles are dispatched near-full.")
    add("- Jemmal fills `booked_seats`, Monastir fills `seats_booked`; load factor uses the combined seat count. "
        "Monastir only records `vehicle_capacity` on 33% of trips — treat its fleet numbers as indicative, not exhaustive.")
    add("")
    add("## 5. Cancellations")
    add("")
    add("| Station | Cancelled | Rate | Top reason |")
    add("|---|---:|---:|---|")
    for st in ["jemmal", "monastir"]:
        ca = canc[st]
        reason = next(iter(ca["reasons"]), "—")
        add(f"| {st.capitalize()} | {ca['cancelled']} | {ca['cancel_rate']:.3%} | {reason} |")
    add("")
    add("- Cancellation is **near-zero** in production (0.005%); cancellation analytics is not actionable until more data exists.")
    add("")
    add("## 6. Key implications for forecasting (Phase 3)")
    add("")
    add("1. **Forecast on ghost/all bookings for volume** (flow is generated even for drafts) but **forecast revenue on the real subset** — mixing them distorts revenue prediction by ~10-15x.")
    add("2. Data is only ~2 months old at Jemmal → **lean on hour-of-day / day-of-week seasonality**, use a 7-day horizon.")
    add("3. Monastir ghost rate (~99%) means its 'revenue' is not meaningful yet — treat Monastir revenue forecasts with caution.")
    add("4. Strong morning (Jemmal) / midday (Monastir) peaks → capacity planning should align dispatch to those windows.")
    add("")
    add("## Charts")
    add("")
    add("| Chart | File |")
    add("|---|---|")
    for p in sorted(CHARTS.glob("*.png")):
        add(f"| {p.stem.replace('_', ' ').title()} | `charts/{p.name}` |")

    (OUT.parent / "STATS_REPORT.md").write_text("\n".join(L))
    print("Wrote STATS_REPORT.md")


if __name__ == "__main__":
    main()
