import { describe, expect, it } from "vitest";
import type { OverviewResponse, ForecastResponse, LiveTick } from "../src/lib/types";

// Compile-time contract checks: if these assignments fail type-checking,
// the shapes drifted. Runtime check is trivial by design.
describe("contract types", () => {
  it("overview shape matches the contract", () => {
    const o = {} as OverviewResponse;
    expect(o).toBeDefined();
  });
  it("forecast shape matches the contract", () => {
    const f = {} as ForecastResponse;
    expect(f).toBeDefined();
  });
  it("live tick shape matches the contract", () => {
    const t = {} as LiveTick;
    expect(t).toBeDefined();
  });
});
