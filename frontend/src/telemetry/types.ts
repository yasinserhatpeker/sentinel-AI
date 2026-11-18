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
export interface OverviewService {
  service: string;
  status: "healthy" | "degraded";
  last_window: string | null;
  request_count: number | null;
  error_rate_percent: number | null;
  p95_latency_ms: number | null;
  cpu_percent: number | null;
  memory_mb: number | null;
  db_connections: number | null;
  db_query_p95_ms: number | null;
  queue_depth: number | null;
  queue_oldest_age_seconds: number | null;
  failed_task_count: number | null;
  anomaly: { score: number | null; severity: "normal" | "warning" | "critical"; detector_type: string } | null;
  fault: OverviewFault | null;
}
export interface SystemOverviewResponse { schema_version: "overview.v2"; environment: "local"; services: OverviewService[]; healthy_service_count: number; degraded_service_count: number; slowest_service: { service: string; p95_latency_ms: number } | null; busiest_queue: { service: string; queue_depth: number } | null; open_incidents: null; highest_anomaly_score: { service: string; score: number | null; raw_score: number | null; severity: "normal" | "warning" | "critical" } | null; active_fault_count: number; recovering_fault_count: number; active_faults: OverviewFault[]; recovering_faults: OverviewFault[]; fault_context_available: boolean; latest_fault: OverviewFault | null; latest_completed_fault: OverviewFault | null; dependencies: Array<[string, string]>; }

export class TelemetryApiError extends Error {
  constructor(public readonly code: string, public readonly status: number, message = "Telemetry request failed") {
    super(message);
  }
}
