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
export interface OverviewFault { id: string; service: string; fault_type: string; status: string; started_at: string | null }
export interface SystemOverviewResponse { schema_version: "overview.v2"; environment: "local"; services: Array<{ service: string; status: "healthy" | "degraded"; p95_latency_ms: number | null; queue_depth: number | null }>; healthy_service_count: number; degraded_service_count: number; slowest_service: { service: string; p95_latency_ms: number } | null; busiest_queue: { service: string; queue_depth: number } | null; open_incidents: null; highest_anomaly_score: { service: string; score: number | null; raw_score: number | null; severity: "normal" | "warning" | "critical" } | null; active_fault_count: number; recovering_fault_count: number; active_faults: OverviewFault[]; recovering_faults: OverviewFault[]; fault_context_available: boolean; latest_fault: OverviewFault | null; latest_completed_fault: OverviewFault | null; dependencies: Array<[string, string]>; }

export class TelemetryApiError extends Error {
  constructor(public readonly code: string, public readonly status: number, message = "Telemetry request failed") {
    super(message);
  }
}
