"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useLiveTick } from "@/lib/ws";
import { isMockMode } from "@/lib/api";
import { Badge } from "./ui";

const NAV = [
  { href: "/", label: "Overview" },
  { href: "/flow", label: "Passenger Flow" },
  { href: "/revenue", label: "Revenue" },
  { href: "/routes", label: "Routes" },
  { href: "/fleet", label: "Fleet" },
  { href: "/forecast", label: "Forecast" },
  { href: "/anomalies", label: "Anomalies" },
];

export default function Shell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const tick = useLiveTick();

  return (
    <div className="flex min-h-screen">
      <aside className="fixed inset-y-0 left-0 flex w-56 flex-col border-r border-[var(--border)] bg-[var(--surface)]">
        <div className="px-5 py-6">
          <p className="text-lg font-bold tracking-tight">
            Wasla<span className="text-[var(--accent)]"> Analytics</span>
          </p>
          <p className="mt-1 text-xs text-[var(--text-dim)]">Jemmal & Monastir stations</p>
        </div>
        <nav className="flex-1 space-y-1 px-3">
          {NAV.map((item) => {
            const active = pathname === item.href;
            return (
              <Link
                key={item.href}
                href={item.href}
                className={`block rounded-lg px-3 py-2 text-sm transition-colors ${
                  active
                    ? "bg-[var(--accent)]/10 font-medium text-[var(--accent)]"
                    : "text-[var(--text-dim)] hover:bg-[var(--surface-2)] hover:text-[var(--text)]"
                }`}
              >
                {item.label}
              </Link>
            );
          })}
        </nav>
        <div className="border-t border-[var(--border)] px-5 py-4 text-[11px] text-[var(--text-dim)]">
          Wasla Analytics Internship — Phase 4/5
        </div>
      </aside>

      <div className="ml-56 flex-1">
        <header className="sticky top-0 z-10 flex items-center justify-between border-b border-[var(--border)] bg-[var(--bg)]/90 px-6 py-3 backdrop-blur">
          <h1 className="text-sm font-semibold text-[var(--text)]">
            {NAV.find((n) => n.href === pathname)?.label ?? "Overview"}
          </h1>
          <div className="flex items-center gap-2">
            <Badge tone={isMockMode() ? "warn" : "default"}>
              {isMockMode() ? "mock data" : "live API"}
            </Badge>
            {tick ? (
              <Badge tone={tick.live ? "good" : "bad"}>
                {tick.live ? `live · ${new Date(tick.at).toLocaleTimeString()}` : "tunnels down"}
              </Badge>
            ) : null}
          </div>
        </header>
        <main className="px-6 py-6">{children}</main>
      </div>
    </div>
  );
}
