"use client";

import AsyncView from "@/components/AsyncView";
import { Badge, Card, CardTitle, DataTable, SourceCaption, fmtInt, fmtPct, fmtTND } from "@/components/ui";
import { C, TrendChart } from "@/components/charts";
import { fetchRevenue } from "@/lib/api";

export default function RevenuePage() {
  return (
    <AsyncView load={fetchRevenue} label="revenue">
      {(data) => {
        const daily = data.daily.map((d) => ({
          created_date: d.created_date,
          "Passenger-paid": Math.round(d.passenger_paid),
          "Station fee": Math.round(d.station_fee),
          "Real only": Math.round(d.real_passenger_paid),
        }));
        return (
          <div className="space-y-6">
            <Card>
              <CardTitle sub="Two definitions, always labeled — passenger-paid includes the driver's base fare; station fee is what the station keeps (seats × 0.15 TND)">
                Daily revenue — both definitions
              </CardTitle>
              <TrendChart
                data={daily}
                xKey="created_date"
                series={[
                  { key: "Passenger-paid", name: "Passenger-paid", color: C.jemmal },
                  { key: "Station fee", name: "Station fee", color: C.ghost },
                  { key: "Real only", name: "Passenger-paid (real only)", color: C.real, dashed: true },
                ]}
                height={320}
                yFmt={(v) => fmtTND(v)}
              />
              <SourceCaption file="Phase_1/data/features/bookings_enriched.parquet (daily aggregate)" />
            </Card>

            <Card>
              <CardTitle sub="Passenger-paid revenue split by booking type — ghost bookings dominate volume but not revenue">
                Real vs ghost revenue
              </CardTitle>
              <TrendChart
                data={data.real_vs_ghost.map((d) => ({ date: d.date, Real: Math.round(d.real), Ghost: Math.round(d.ghost) }))}
                xKey="date"
                series={[
                  { key: "Real", name: "Real", color: C.real },
                  { key: "Ghost", name: "Ghost", color: C.ghost },
                ]}
                height={280}
                yFmt={(v) => fmtTND(v)}
              />
              <SourceCaption file="Phase_1/data/features/bookings_enriched.parquet" />
            </Card>

            <Card>
              <CardTitle sub="Top routes by passenger-paid revenue">Revenue by route</CardTitle>
              <DataTable
                rows={data.by_route.filter((r) => r.bookings > 0)}
                rowKey={(r) => `${r.station}-${r.destination_canonical}`}
                columns={[
                  { key: "station", label: "Station" },
                  { key: "destination_canonical", label: "Route" },
                  { key: "bookings", label: "Bookings", format: (v) => fmtInt(Number(v)) },
                  { key: "revenue_passenger_paid", label: "Passenger-paid", format: (v) => fmtTND(Number(v)) },
                  { key: "revenue_station_fee", label: "Station fee", format: (v) => fmtTND(Number(v)) },
                  { key: "avg_ticket", label: "Avg ticket", format: (v) => fmtTND(Number(v)) },
                  { key: "ghost_rate", label: "Ghost rate", format: (v) => <Badge tone={Number(v) > 0.9 ? "warn" : "good"}>{fmtPct(Number(v))}</Badge> },
                ]}
              />
              <SourceCaption file="Phase_1/data/features/bookings_enriched.parquet (route aggregate)" />
            </Card>
          </div>
        );
      }}
    </AsyncView>
  );
}
