import type {
  AnomaliesResponse,
  FleetResponse,
  FlowDailyResponse,
  FlowHourlyResponse,
  ForecastResponse,
  HealthResponse,
  OverviewResponse,
  RevenueResponse,
  RoutesResponse,
} from "./types";

export function isMockMode(): boolean {
  return process.env.NEXT_PUBLIC_USE_MOCK === "1";
}

export function apiBase(): string {
  return process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000";
}

async function get<T>(name: string): Promise<T> {
  if (isMockMode()) {
    const res = await fetch(`/mock/${name}.json`);
    if (!res.ok) throw new Error(`mock ${name}: HTTP ${res.status}`);
    return (await res.json()) as T;
  }
  const res = await fetch(`${apiBase()}/api/${name}`, { cache: "no-store" });
  if (!res.ok) throw new Error(`api ${name}: HTTP ${res.status}`);
  return (await res.json()) as T;
}

export const fetchOverview = () => get<OverviewResponse>("overview");
export const fetchFlowHourly = () => get<FlowHourlyResponse>("flow_hourly");
export const fetchFlowDaily = () => get<FlowDailyResponse>("flow_daily");
export const fetchRevenue = () => get<RevenueResponse>("revenue");
export const fetchRoutes = () => get<RoutesResponse>("routes");
export const fetchFleet = () => get<FleetResponse>("fleet");
export const fetchForecast = () => get<ForecastResponse>("forecast");
export const fetchAnomalies = () => get<AnomaliesResponse>("anomalies");
export const fetchHealth = () => get<HealthResponse>("health");

/** WebSocket URL for the live feed; null when in mock mode. */
export function liveWsUrl(): string | null {
  if (isMockMode()) return null;
  return `${apiBase().replace(/^http/, "ws")}/ws/live`;
}
