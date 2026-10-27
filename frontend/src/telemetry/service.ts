import type { SystemOverviewResponse, TelemetryAggregateResponse, TelemetryServicesResponse } from "./types";
import { TelemetryApiError } from "./types";

function headers(token: string): HeadersInit {
  return { Authorization: `Bearer ${token}` };
}

async function readJson<T>(path: string, token: string): Promise<T> {
  const response = await fetch(path, { headers: headers(token) });
  if (!response.ok) {
    const body = (await response.json().catch(() => null)) as { error?: { code?: string } } | null;
    throw new TelemetryApiError(body?.error?.code ?? "request_failed", response.status);
  }
  return response.json() as Promise<T>;
}

export function getServices(token: string, environment: "local") {
  return readJson<TelemetryServicesResponse>(`/api/telemetry/v1/services/?environment=${environment}`, token);
}
export function getSystemOverview(token: string) { return readJson<SystemOverviewResponse>("/api/telemetry/v1/overview/?environment=local", token); }

export function getAggregates(
  token: string,
  scope: { environment: "local"; service: string; start: string; end: string },
) {
  const query = new URLSearchParams(scope);
  return readJson<TelemetryAggregateResponse>(`/api/telemetry/v1/aggregates/?${query}`, token);
}
