import { describe, expect, it } from "vitest";
import { fmtInt, fmtPct, fmtTND } from "../src/lib/format";

describe("format helpers", () => {
  it("fmtInt groups thousands", () => {
    expect(fmtInt(1234567)).toBe("1,234,567");
  });
  it("fmtTND appends currency", () => {
    expect(fmtTND(179123.456)).toBe("179,123 TND");
  });
  it("fmtPct renders one decimal", () => {
    expect(fmtPct(0.968)).toBe("96.8%");
  });
});
