"use client";

import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

export const C = {
  grid: "#1d2a3f",
  axis: "#8fa3bd",
  jemmal: "#38bdf8",
  monastir: "#f59e0b",
  real: "#34d399",
  ghost: "#5b6b84",
  forecast: "#a78bfa",
  actual: "#e6edf6",
};

const tooltipStyle = {
  backgroundColor: "#0d1420",
  border: "1px solid #1d2a3f",
  borderRadius: 8,
  fontSize: 12,
  color: "#e6edf6",
};

export interface TrendSeries {
  key: string;
  name: string;
  color: string;
  dashed?: boolean;
}

export function TrendChart({
  data,
  series,
  xKey,
  height = 280,
  yFmt,
}: {
  data: Record<string, unknown>[];
  series: TrendSeries[];
  xKey: string;
  height?: number;
  yFmt?: (v: number) => string;
}) {
  return (
    <ResponsiveContainer width="100%" height={height}>
      <LineChart data={data} margin={{ top: 8, right: 12, bottom: 0, left: 0 }}>
        <CartesianGrid stroke={C.grid} strokeDasharray="3 3" vertical={false} />
        <XAxis dataKey={xKey} tick={{ fill: C.axis, fontSize: 11 }} tickLine={false} axisLine={{ stroke: C.grid }} minTickGap={24} />
        <YAxis
          tick={{ fill: C.axis, fontSize: 11 }}
          tickLine={false}
          axisLine={false}
          width={64}
          tickFormatter={(v: number) => (yFmt ? yFmt(v) : String(v))}
        />
        <Tooltip contentStyle={tooltipStyle} formatter={yFmt ? (v) => yFmt(Number(v)) : undefined} />
        <Legend wrapperStyle={{ fontSize: 12 }} />
        {series.map((s) => (
          <Line
            key={s.key}
            type="monotone"
            dataKey={s.key}
            name={s.name}
            stroke={s.color}
            strokeWidth={2}
            dot={false}
            strokeDasharray={s.dashed ? "6 3" : undefined}
          />
        ))}
      </LineChart>
    </ResponsiveContainer>
  );
}
