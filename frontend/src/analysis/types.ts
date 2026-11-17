export type Severity = "normal" | "warning" | "critical";
export type AnalysisScope = { environment: "local"; service: string; start: string; end: string; limit?: string };

export interface Anomaly {
  id: string; environment: "local"; service: string; window_start: string;
  detector_type: string; detector_version: string; configuration_version: string;
  model_version: string | null; score: number | null; threshold: number | null;
  raw_score: number | null; raw_threshold: number | null;
  is_anomaly: boolean; severity: Severity; reasons: string[];
  evidence?: Record<string, number | string | null>;
}
export interface AnomalyListResponse { schema_version: "anomalies.v1"; scope: AnalysisScope; results: Anomaly[] }
export interface AnomalyDetailResponse { schema_version: "anomalies.v1"; anomaly: Anomaly }

export interface FaultExperiment {
  id: string; environment: "local"; service: string; fault_type: string; status: string;
  parameters: Record<string, number>; duration_seconds: number; seed: number;
  repeated_from: string | null; created_at: string; started_at: string | null;
  expires_at: string | null; stopped_at: string | null; recovery_until: string | null;
  failure_reason: string | null;
}
export interface FaultListResponse { schema_version: "fault-experiments.v1"; results: FaultExperiment[] }
export interface FaultResponse { schema_version: "fault-experiments.v1"; experiment: FaultExperiment }

export interface DetectorModel {
  id: string; model_version: string; detector_type: string; detector_version: string;
  feature_schema_version: string; environment: "local"; service: string; status: string;
  configuration: Record<string, number>; feature_count: number; sample_count: number;
  trained_from: string; trained_until: string; created_at: string; activated_at: string | null;
  artifact_available: boolean;
}
export interface ModelListResponse { schema_version: "models.v1"; results: DetectorModel[] }
export interface ModelResponse { schema_version: "models.v1"; model: DetectorModel }
export interface ModelReadinessResponse {
  schema_version: "model-readiness.v1"; scope: AnalysisScope;
  status: "collecting" | "partial" | "isolation_forest_ready" | "lstm_ready";
  feature_sample_count: number; eligible_isolation_forest_sample_count: number;
  isolation_forest_minimum_samples: number; isolation_forest_ready: boolean;
  first_window: string | null; last_window: string | null;
  longest_contiguous_window_count: number; sequence_gap_count: number;
  missing_value_count: number; missing_value_ratio: number | null;
  sequence_length: number; candidate_sequence_count: number; materialized_sequence_count: number;
  sequence_split_counts: { train: number; validation: number; test: number };
  lstm_minimum_sequences: number; lstm_ready: boolean;
  windows_remaining_for_lstm: number; estimated_minutes_remaining_for_lstm: number;
}
export interface LstmPrototypeResult {
  schema_version: "lstm-prototype-result.v1"; environment: "local"; service: string;
  materialized_sequence_count: number; sequence_length: number; epochs: number; seed: number;
  train_samples: number; validation_samples: number; test_samples: number;
  validation_accuracy: number; test_accuracy: number; activated: false;
}

export interface DetectorEvaluation {
  id: string; experiment_id: string; detector_type: string; detector_version: string;
  configuration_version: string; model_version: string | null;
  confusion: { true_positive: number; false_positive: number; true_negative: number; false_negative: number };
  precision: number; recall: number; f1_score: number; false_positive_rate: number;
  detection_delay_seconds: number | null; recovery_delay_seconds: number | null; evaluated_at: string;
}
export interface EvaluationListResponse { schema_version: "evaluations.v1"; results: DetectorEvaluation[] }
