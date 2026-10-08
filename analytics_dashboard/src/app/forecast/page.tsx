"use client";

import AsyncView from "@/components/AsyncView";
import { Card, CardTitle, SourceCaption, fmtInt, fmtPct } from "@/components/ui";
import { C, TrendChart } from "@/components/charts";
import { fetchForecast } from "@/lib/api";

const KEY_LABEL: Record<string, string> = { jemmal: "Jemmal", monastir: "Monastir", total: "Total" };

export default function ForecastPage() {
  return (
    <AsyncView load={fetchForecast} label="forecast">
      {(data) => (
        <div className="space-y-6">
          <div className="rounded-xl border border-[var(--border)] bg-[var(--surface)] p-4 text-sm text-[var(--text-dim)]">
            {data.disclaimer}
          </div>

          {data.forecasts.map((f) => {
            const forecast = f.forecast.map((p) => ({
              date: p.date,
              Forecast: Math.round(p.yhat),
              Lo: Math.round(p.lo),
              Hi: Math.round(p.hi),
            }));
            const pva = data.pred_vs_actual
              .filter((p) => p.station === f.station)
              .map((p) => ({ date: p.date, Actual: p.actual, Predicted: Math.round(p.predicted) }));
            return (
              <Card key={f.station}>
                <CardTitle sub={`Model: ${f.model} · horizon ${f.horizon_days} days · walk-forward CV MAPE ${
                  f.mape != null ? `${fmtPct(f.mape)} ± ${fmtPct(f.mape_std ?? 0)}` : "n/a"
                }`}>
                  {KEY_LABEL[f.station] ?? f.station} — 7-day forecast
                </CardTitle>
                <TrendChart
                  data={forecast}
                  xKey="date"
                  series={[
                    { key: "Forecast", name: "Forecast", color: C.forecast },
                    { key: "Lo", name: "Lower band", color: C.ghost, dashed: true },
                    { key: "Hi", name: "Upper band", color: C.ghost, dashed: true },
                  ]}
                  height={260}
                  yFmt={(v) => fmtInt(v)}
                />
                {pva.length > 0 ? (
                  <>
                    <p className="mt-6 text-xs uppercase tracking-wider text-[var(--text-dim)]">
                      Last 2 weeks — predicted vs actual
                    </p>
                    <div className="mt-2">
                      <TrendChart
                        data={pva}
                        xKey="date"
                        series={[
                          { key: "Actual", name: "Actual", color: C.actual },
                          { key: "Predicted", name: "Predicted", color: C.forecast, dashed: true },
                        ]}
                        height={240}
                        yFmt={(v) => fmtInt(v)}
                      />
                    </div>
                  </>
                ) : (
                  <p className="mt-4 text-xs text-[var(--text-dim)]">
                    In-sample comparison not shown — {f.model} in-sample predictions are not persisted.
                  </p>
                )}
                <SourceCaption file="Phase_3/models/model_meta_*.json + Phase_3/output/series_*.parquet" />
              </Card>
            );
          })}
        </div>
      )}
    </AsyncView>
  );
}
