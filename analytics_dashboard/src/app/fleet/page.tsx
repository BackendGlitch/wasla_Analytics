"use client";

import AsyncView from "@/components/AsyncView";
import { Card, CardTitle, KpiCard, SourceCaption, fmtInt, fmtPct } from "@/components/ui";
import { C, TrendChart } from "@/components/charts";
import { fetchFleet } from "@/lib/api";

export default function FleetPage() {
  return (
    <AsyncView load={fetchFleet} label="fleet">
      {(data) => (
        <div className="space-y-6">
          <div className="rounded-xl border border-amber-500/30 bg-amber-500/10 p-4 text-sm text-amber-200">
            {data.caveat}
          </div>
          <div className="grid gap-6 xl:grid-cols-2">
            {(["jemmal", "monastir"] as const).map((st) => {
              const s = data.summary[st];
              return (
                <Card key={st}>
                  <CardTitle sub={st === "jemmal" ? "Jemmal station" : "Monastir station"}>
                    Fleet — {st === "jemmal" ? "Jemmal" : "Monastir"}
                  </CardTitle>
                  <div className="grid grid-cols-2 gap-3">
                    <KpiCard label="Vehicles seen" value={fmtInt(s.active_vehicles)} />
                    <KpiCard label="Trips per vehicle" value={s.trips_per_vehicle.toFixed(1)} />
                    <KpiCard
                      label="Avg load factor"
                      value={s.avg_load_factor != null ? fmtPct(s.avg_load_factor) : "—"}
                      tone={s.avg_load_factor != null && s.avg_load_factor > 0.85 ? "good" : "default"}
                    />
                    <KpiCard
                      label="Capacity coverage"
                      value={s.capacity_coverage_pct != null ? fmtPct(s.capacity_coverage_pct) : "—"}
                      tone={s.capacity_coverage_pct != null && s.capacity_coverage_pct < 0.5 ? "warn" : "default"}
                    />
                  </div>
                </Card>
              );
            })}
          </div>
          <Card>
            <CardTitle sub="Daily trips and mean load factor per station">Fleet activity over time</CardTitle>
            <TrendChart
              data={data.daily.map((d) => ({
                date: d.date,
                [`${d.station} trips`]: d.trips,
              }))}
              xKey="date"
              series={[
                { key: "jemmal trips", name: "Jemmal trips", color: C.jemmal },
                { key: "monastir trips", name: "Monastir trips", color: C.monastir },
              ]}
              height={300}
              yFmt={(v) => fmtInt(v)}
            />
            <SourceCaption file="Phase_1/data/clean/trips.parquet + Phase_2/output/fleet_stats.json" />
          </Card>
        </div>
      )}
    </AsyncView>
  );
}
