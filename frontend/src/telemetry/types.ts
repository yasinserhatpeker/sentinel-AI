export type MetricGroup = "http" | "runtime" | "database" | "queue";

export interface TelemetryPoint {
  timestamp: string;
  metric: string;
  unit: string;
  count: number;
  minimum: number;
  maximum: number;
  average: number;
  last: number;
  p50: number;
  p95: number;
  p99: number;
}

export interface TelemetryAggregateResponse {
  schema_version: "telemetry.v1";
  scope: { environment: "local"; service: string; start: string; end: string };
  availability: Record<MetricGroup, boolean>;
  points: TelemetryPoint[];
}

export interface TelemetryServicesResponse {
  environment: "local";
  services: string[];
}

export class TelemetryApiError extends Error {
  constructor(public readonly code: string, message = "Telemetry request failed") {
    super(message);
  }
}
