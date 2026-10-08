"use client";

import AsyncView from "@/components/AsyncView";
import { Card, CardTitle, SourceCaption } from "@/components/ui";
import { C, TrendChart } from "@/components/charts";
import { fetchFlowDaily, fetchFlowHourly } from "@/lib/api";
import { fmtInt } from "@/lib/format";

const perStation = <T,>(series: T[], get: (r: T) => string) => (station: string) =>
  series.filter((r) => get(r) === station);

export default function FlowPage() {
  return (
    <div className="space-y-6">
      <AsyncView load={fetchFlowHourly} label="hourly flow">
        {(hourly) => {
          const by = perStation(hourly.series, (r) => r.station);
          const jemmal = by("jemmal").map((r) => ({ hour: `${String(r.hour).padStart(2, "0")}h`, Jemmal: r.bookings }));
          const monastir = by("monastir").map((r) => ({ hour: `${String(r.hour).padStart(2, "0")}h`, Monastir: r.bookings }));
          const overlay = hourly.series.reduce<Record<string, Record<string, number>>>((acc, r) => {
            const k = `${String(r.hour).padStart(2, "0")}h`;
            (acc[k] ??= {})[r.station === "jemmal" ? "Jemmal" : "Monastir"] = r.bookings;
            return acc;
          }, {});
          const data = Object.entries(overlay)
            .map(([hour, v]) => ({ hour, ...v }))
            .sort((a, b) => a.hour.localeCompare(b.hour));
          return (
            <>
              <Card>
                <CardTitle sub="Hourly booking curve per station — Jemmal peaks ~06h, Monastir ~12h">
                  Hourly passenger flow (all bookings)
                </CardTitle>
                <TrendChart
                  data={data}
                  xKey="hour"
                  series={[
                    { key: "Jemmal", name: "Jemmal", color: C.jemmal },
                    { key: "Monastir", name: "Monastir", color: C.monastir },
                  ]}
                  yFmt={(v) => fmtInt(v)}
                />
                <SourceCaption file="Phase_1/data/features/bookings_enriched.parquet (hourly aggregate)" />
              </Card>
              <div className="grid gap-6 xl:grid-cols-2">
                <Card>
                  <CardTitle sub="Total bookings by hour">Jemmal</CardTitle>
                  <TrendChart
                    data={jemmal}
                    xKey="hour"
                    series={[{ key: "Jemmal", name: "Jemmal", color: C.jemmal }]}
                    yFmt={(v) => fmtInt(v)}
                  />
                </Card>
                <Card>
                  <CardTitle sub="Total bookings by hour">Monastir</CardTitle>
                  <TrendChart
                    data={monastir}
                    xKey="hour"
                    series={[{ key: "Monastir", name: "Monastir", color: C.monastir }]}
                    yFmt={(v) => fmtInt(v)}
                  />
                </Card>
              </div>
            </>
          );
        }}
      </AsyncView>

      <AsyncView load={fetchFlowDaily} label="daily flow">
        {(daily) => {
          const merged: Record<string, Record<string, number>> = {};
          for (const r of daily.series) {
            (merged[r.created_date] ??= {})[r.station === "jemmal" ? "Jemmal" : "Monastir"] = r.bookings;
          }
          const data = Object.entries(merged)
            .map(([date, v]) => ({ date, ...v }))
            .sort((a, b) => a.date.localeCompare(b.date));
          const total = daily.series.reduce((s, r) => s + r.bookings, 0);
          return (
            <Card>
              <CardTitle sub={`Daily bookings · ${fmtInt(total)} total across both stations`}>
                Daily passenger flow
              </CardTitle>
              <TrendChart
                data={data}
                xKey="date"
                series={[
                  { key: "Jemmal", name: "Jemmal", color: C.jemmal },
                  { key: "Monastir", name: "Monastir", color: C.monastir },
                ]}
                height={320}
                yFmt={(v) => fmtInt(v)}
              />
              <SourceCaption file="Phase_1/data/features/bookings_enriched.parquet (daily aggregate)" />
            </Card>
          );
        }}
      </AsyncView>
    </div>
  );
}
