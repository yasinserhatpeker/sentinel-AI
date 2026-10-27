import type { MetricGroup, TelemetryAggregateResponse } from "./types";

export type DashboardState = "loading" | "error" | "empty-services" | "empty-data" | "partial" | "ready";

export function dashboardState(input: {
  loading: boolean;
  errorCode: string;
  services: string[];
  response: TelemetryAggregateResponse | null;
}): DashboardState {
  if (input.loading) return "loading";
  if (input.errorCode) return "error";
  if (!input.services.length) return "empty-services";
  if (!input.response?.points.length) return "empty-data";
  if ((Object.keys(input.response.availability) as MetricGroup[]).some((group) => !input.response?.availability[group])) {
    return "partial";
  }
  return "ready";
}
