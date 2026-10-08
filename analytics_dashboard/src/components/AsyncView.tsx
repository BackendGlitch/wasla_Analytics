"use client";

import { useEffect, useState } from "react";

/**
 * Fetch-on-mount wrapper: renders skeleton, error (with retry), then data.
 * Every page uses this so loading/empty/error handling is identical.
 */
export default function AsyncView<T>({
  load,
  children,
  label,
}: {
  load: () => Promise<T>;
  children: (data: T) => React.ReactNode;
  label: string;
}) {
  const [state, setState] = useState<{ status: "loading" | "error" | "ok"; data?: T; error?: string }>({
    status: "loading",
  });

  const run = () => {
    setState({ status: "loading" });
    load()
      .then((data) => setState({ status: "ok", data }))
      .catch((e: unknown) => setState({ status: "error", error: e instanceof Error ? e.message : String(e) }));
  };

  // Initial fetch: no synchronous setState in the effect body
  // (react-hooks/set-state-in-effect) — state already starts as "loading".
  useEffect(() => {
    let cancelled = false;
    load()
      .then((data) => {
        if (!cancelled) setState({ status: "ok", data });
      })
      .catch((e: unknown) => {
        if (!cancelled) setState({ status: "error", error: e instanceof Error ? e.message : String(e) });
      });
    return () => {
      cancelled = true;
    };
  }, [load]);

  if (state.status === "loading") {
    return <p className="animate-pulse text-sm text-[var(--text-dim)]">Loading {label}…</p>;
  }
  if (state.status === "error") {
    return (
      <div className="rounded-xl border border-red-500/30 bg-red-500/10 p-5 text-sm">
        <p className="font-medium text-red-300">Could not load {label}.</p>
        <p className="mt-1 text-red-200/70">{state.error}</p>
        <button
          onClick={run}
          className="mt-3 rounded-lg border border-red-500/40 px-3 py-1.5 text-xs text-red-200 hover:bg-red-500/10"
        >
          Retry
        </button>
      </div>
    );
  }
  return <>{children(state.data as T)}</>;
}
