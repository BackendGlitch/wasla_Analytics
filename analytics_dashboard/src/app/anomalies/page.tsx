"use client";

import AsyncView from "@/components/AsyncView";
import { Badge, Card, CardTitle, DataTable, SourceCaption, fmtInt } from "@/components/ui";
import { fetchAnomalies } from "@/lib/api";

const KEY_LABEL: Record<string, string> = { jemmal: "Jemmal", monastir: "Monastir", total: "Total" };

export default function AnomaliesPage() {
  return (
    <AsyncView load={fetchAnomalies} label="anomalies">
      {(data) => (
        <div className="space-y-6">
          <Card>
            <CardTitle sub={`Consensus of 3 detectors (rolling z-score, week-over-week z-score, IsolationForest) + zero-day rule · ${data.anomalies.length} flagged days`}>
              Detected anomalies
            </CardTitle>
            <DataTable
              rows={data.anomalies}
              rowKey={(r) => `${r.station}-${r.date}`}
              columns={[
                { key: "date", label: "Date" },
                { key: "station", label: "Series", format: (v) => KEY_LABEL[String(v)] ?? String(v) },
                { key: "bookings", label: "Bookings", format: (v) => fmtInt(Number(v)) },
                { key: "detectors", label: "Detectors fired", format: (v) => String(v).split(",").filter(Boolean).map((d) => <Badge key={d}>{d}</Badge>) },
                { key: "zero_day", label: "Zero day", format: (v) => (v ? <Badge tone="bad">zero bookings</Badge> : "—") },
              ]}
            />
            <SourceCaption file="Phase_3/output/anomaly_summary.json" />
          </Card>
        </div>
      )}
    </AsyncView>
  );
}
