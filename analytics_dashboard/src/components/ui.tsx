import { fmtInt, fmtPct, fmtTND } from "@/lib/format";

export function Card({ children, className = "" }: { children: React.ReactNode; className?: string }) {
  return (
    <section
      className={`rounded-xl border border-[var(--border)] bg-[var(--surface)] p-5 ${className}`}
    >
      {children}
    </section>
  );
}

export function CardTitle({ children, sub }: { children: React.ReactNode; sub?: string }) {
  return (
    <div className="mb-4">
      <h2 className="text-sm font-semibold tracking-wide text-[var(--text)]">{children}</h2>
      {sub ? <p className="mt-1 text-xs text-[var(--text-dim)]">{sub}</p> : null}
    </div>
  );
}

/** Traceability caption — every view shows which artifact feeds it. */
export function SourceCaption({ file }: { file: string }) {
  return (
    <p className="mt-3 text-[11px] text-[var(--text-dim)]/70">
      Source: <code className="text-[11px]">{file}</code>
    </p>
  );
}

export function KpiCard({
  label,
  value,
  hint,
  tone = "default",
}: {
  label: string;
  value: string;
  hint?: string;
  tone?: "default" | "good" | "warn" | "bad" | "accent";
}) {
  const tones: Record<string, string> = {
    default: "text-[var(--text)]",
    good: "text-[var(--good)]",
    warn: "text-[var(--warn)]",
    bad: "text-[var(--bad)]",
    accent: "text-[var(--accent)]",
  };
  return (
    <Card className="min-w-0">
      <p className="text-xs uppercase tracking-wider text-[var(--text-dim)]">{label}</p>
      <p className={`mt-2 truncate text-2xl font-semibold tabular-nums ${tones[tone]}`}>{value}</p>
      {hint ? <p className="mt-1 text-xs text-[var(--text-dim)]">{hint}</p> : null}
    </Card>
  );
}

export function Badge({ children, tone = "default" }: { children: React.ReactNode; tone?: "default" | "good" | "warn" | "bad" }) {
  const tones: Record<string, string> = {
    default: "bg-[var(--surface-2)] text-[var(--text-dim)] border-[var(--border)]",
    good: "bg-emerald-500/10 text-emerald-300 border-emerald-500/30",
    warn: "bg-amber-500/10 text-amber-300 border-amber-500/30",
    bad: "bg-red-500/10 text-red-300 border-red-500/30",
  };
  return (
    <span className={`inline-flex items-center rounded-full border px-2 py-0.5 text-[11px] font-medium ${tones[tone]}`}>
      {children}
    </span>
  );
}

export function DataTable<T>({
  columns,
  rows,
  rowKey,
}: {
  columns: { key: string; label: string; format?: (v: unknown, row: T) => React.ReactNode }[];
  rows: T[];
  rowKey: (row: T) => string;
}) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full border-collapse text-sm">
        <thead>
          <tr className="border-b border-[var(--border)] text-left text-xs uppercase tracking-wider text-[var(--text-dim)]">
            {columns.map((c) => (
              <th key={c.key} className="py-2 pr-4 font-medium">{c.label}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => (
            <tr key={rowKey(r)} className="border-b border-[var(--border)]/50 last:border-0">
              {columns.map((c) => (
                <td key={c.key} className="py-2 pr-4 tabular-nums">
                  {c.format ? c.format((r as Record<string, unknown>)[c.key], r) : String((r as Record<string, unknown>)[c.key] ?? "")}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export { fmtInt, fmtPct, fmtTND };
