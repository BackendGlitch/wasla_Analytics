"use client";

import AsyncView from "@/components/AsyncView";
import { Badge, Card, CardTitle, DataTable, SourceCaption, fmtInt, fmtPct, fmtTND } from "@/components/ui";
import { fetchRoutes } from "@/lib/api";

export default function RoutesPage() {
  return (
    <AsyncView load={fetchRoutes} label="routes">
      {(data) => (
        <div className="space-y-6">
          <Card>
            <CardTitle sub={`Route groups: ${data.groups.join(", ")} — both stations side by side`}>
              Route performance (5 destination routes)
            </CardTitle>
            <DataTable
              rows={data.routes.filter((r) => r.bookings > 0)}
              rowKey={(r) => `${r.station}-${r.destination_canonical}`}
              columns={[
                { key: "station", label: "Station" },
                { key: "destination_canonical", label: "Destination" },
                { key: "bookings", label: "Bookings", format: (v) => fmtInt(Number(v)) },
                { key: "revenue_passenger_paid", label: "Passenger-paid", format: (v) => fmtTND(Number(v)) },
                { key: "revenue_station_fee", label: "Station fee", format: (v) => fmtTND(Number(v)) },
                { key: "avg_ticket", label: "Avg ticket", format: (v) => fmtTND(Number(v)) },
                { key: "ghost_rate", label: "Ghost rate", format: (v) => <Badge tone={Number(v) > 0.9 ? "warn" : "good"}>{fmtPct(Number(v))}</Badge> },
              ]}
            />
            <SourceCaption file="Phase_1/data/features/bookings_enriched.parquet (destination aggregate)" />
          </Card>
        </div>
      )}
    </AsyncView>
  );
}
