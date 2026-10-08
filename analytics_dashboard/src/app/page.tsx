"use client";

import AsyncView from "@/components/AsyncView";
import { Card, CardTitle, KpiCard, SourceCaption, fmtInt, fmtTND } from "@/components/ui";
import { fetchOverview } from "@/lib/api";
import { useLiveTick } from "@/lib/ws";
import type { OverviewStation } from "@/lib/types";

const STATION_LABEL: Record<string, string> = { jemmal: "Jemmal", monastir: "Monastir" };

function StationCards({ name, s }: { name: string; s: OverviewStation }) {
  return (
    <Card>
      <CardTitle sub={`Latest full day · ${name}`}>{name}</CardTitle>
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <KpiCard label="Bookings" value={fmtInt(s.bookings_latest_day)} />
        <KpiCard label="Passenger-paid" value={fmtTND(s.revenue_passenger_paid_latest_day)} tone="accent" />
        <KpiCard label="Station fee" value={fmtTND(s.revenue_station_fee_latest_day)} />
        <KpiCard label="Real / Ghost" value={`${fmtInt(s.real_bookings_latest_day)} / ${fmtInt(s.ghost_bookings_latest_day)}`} />
        <KpiCard label="Trips" value={s.trips_latest_day != null ? fmtInt(s.trips_latest_day) : "—"} />
        <KpiCard label="Active vehicles" value={s.active_vehicles != null ? fmtInt(s.active_vehicles) : "—"} />
      </div>
    </Card>
  );
}

export default function OverviewPage() {
  const tick = useLiveTick();

  return (
    <AsyncView load={fetchOverview} label="overview">
      {(data) => (
        <div className="space-y-6">
          {tick?.live === false ? (
            <div className="rounded-xl border border-amber-500/30 bg-amber-500/10 p-4 text-sm text-amber-200">
              Live feed unavailable — tunnels down. Showing latest cached data through{" "}
              {data.data_through}. Last live tick: {tick.last_seen ?? "never"}.
            </div>
          ) : null}

          <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
            <KpiCard
              label={`Bookings · ${data.data_through}`}
              value={fmtInt(data.totals.bookings_latest_day)}
              hint="both stations, latest full day"
            />
            <KpiCard
              label="Passenger-paid"
              value={fmtTND(data.totals.revenue_passenger_paid_latest_day)}
              hint="what passengers paid (incl. base fare)"
              tone="accent"
            />
            <KpiCard
              label="Station fee"
              value={fmtTND(data.totals.revenue_station_fee_latest_day)}
              hint="seats × 0.15 TND — what the station keeps"
            />
            <KpiCard
              label="Real vs ghost"
              value={`${fmtInt(data.totals.real_bookings_latest_day)} / ${fmtInt(data.totals.ghost_bookings_latest_day)}`}
              hint="verified tickets vs pre-generated drafts"
              tone={data.totals.real_bookings_latest_day > 0 ? "good" : "warn"}
            />
          </div>

          {(data.anomaly_today.jemmal || data.anomaly_today.monastir) ? (
            <div className="rounded-xl border border-amber-500/40 bg-amber-500/10 p-4">
              <p className="text-sm font-semibold text-amber-300">⚠ Anomaly flagged for the latest day</p>
              {Object.entries(data.anomaly_today)
                .filter(([, f]) => f)
                .map(([st, f]) => (
                  <p key={st} className="mt-1 text-sm text-amber-200/90">
                    {STATION_LABEL[st] ?? st}: {f!.bookings} bookings,{" "}
                    {f!.zero_day ? "zero-day" : "consensus spike"}, detectors: {f!.detectors.join(", ")}
                  </p>
                ))}
            </div>
          ) : (
            <div className="rounded-xl border border-[var(--border)] bg-[var(--surface)] p-4 text-sm text-[var(--text-dim)]">
              No consensus anomaly on the latest full day.
            </div>
          )}

          <div className="grid gap-6 xl:grid-cols-2">
            <StationCards name="Jemmal" s={data.stations.jemmal} />
            <StationCards name="Monastir" s={data.stations.monastir} />
          </div>

          {tick?.live ? (
            <Card>
              <CardTitle sub="Live minutely counts straight from the station databases">Live right now</CardTitle>
              <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
                {Object.entries(tick.stations).map(([st, v]) =>
                  v ? (
                    <KpiCard
                      key={st}
                      label={`${STATION_LABEL[st] ?? st} · today`}
                      value={fmtInt(v.bookings_today)}
                      hint={`${fmtTND(v.revenue_passenger_paid)} · ${v.real} real`}
                      tone={v.anomaly_flag ? "warn" : "default"}
                    />
                  ) : (
                    <KpiCard key={st} label={`${STATION_LABEL[st] ?? st} · today`} value="—" hint="tunnel down" tone="bad" />
                  ),
                )}
              </div>
            </Card>
          ) : null}

          <SourceCaption file="Phase_1/data/features/bookings_enriched.parquet + Phase_2/output/fleet_stats.json + Phase_3/output/anomaly_summary.json" />
        </div>
      )}
    </AsyncView>
  );
}
