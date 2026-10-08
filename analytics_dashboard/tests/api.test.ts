import { afterEach, describe, expect, it, vi } from "vitest";

const fetchMock = vi.fn();
vi.stubGlobal("fetch", fetchMock);

import * as api from "../src/lib/api";

const jsonOk = (body: unknown) =>
  Promise.resolve(new Response(JSON.stringify(body), { status: 200 }));

afterEach(() => {
  fetchMock.mockReset();
  delete process.env.NEXT_PUBLIC_USE_MOCK;
  delete process.env.NEXT_PUBLIC_API_BASE;
});

describe("api data layer", () => {
  it("mock mode fetches /mock/<name>.json", async () => {
    process.env.NEXT_PUBLIC_USE_MOCK = "1";
    fetchMock.mockReturnValueOnce(jsonOk({ data_through: "2026-10-08" }));
    await api.fetchOverview();
    expect(fetchMock).toHaveBeenCalledWith("/mock/overview.json");
  });

  it("api mode fetches ${API_BASE}/api/<name>", async () => {
    process.env.NEXT_PUBLIC_USE_MOCK = "0";
    process.env.NEXT_PUBLIC_API_BASE = "http://example.test:8000";
    fetchMock.mockReturnValueOnce(jsonOk({}));
    await api.fetchAnomalies();
    expect(fetchMock).toHaveBeenCalledWith(
      "http://example.test:8000/api/anomalies",
      { cache: "no-store" },
    );
  });

  it("non-2xx throws with the endpoint name", async () => {
    process.env.NEXT_PUBLIC_USE_MOCK = "1";
    fetchMock.mockReturnValueOnce(
      Promise.resolve(new Response("nope", { status: 500 })),
    );
    await expect(api.fetchOverview()).rejects.toThrow(/overview.*500/i);
  });

  it("liveWsUrl is null in mock mode", () => {
    process.env.NEXT_PUBLIC_USE_MOCK = "1";
    expect(api.liveWsUrl()).toBeNull();
  });

  it("liveWsUrl derives ws:// from the API base", () => {
    process.env.NEXT_PUBLIC_USE_MOCK = "0";
    process.env.NEXT_PUBLIC_API_BASE = "http://localhost:8000";
    expect(api.liveWsUrl()).toBe("ws://localhost:8000/ws/live");
  });
});
