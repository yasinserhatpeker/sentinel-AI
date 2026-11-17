import { TelemetryApiError } from "../telemetry/types";
import type { AnalysisScope, AnomalyDetailResponse, AnomalyListResponse, EvaluationListResponse, FaultListResponse, FaultResponse, LstmPrototypeResult, ModelListResponse, ModelReadinessResponse, ModelResponse } from "./types";

function authHeaders(token: string, json = false): HeadersInit {
  return { Authorization: `Bearer ${token}`, ...(json ? { "Content-Type": "application/json" } : {}) };
}

async function request<T>(path: string, token: string, options: RequestInit = {}): Promise<T> {
  const response = await fetch(path, { ...options, headers: { ...authHeaders(token, Boolean(options.body)), ...(options.headers ?? {}) } });
  if (!response.ok) {
    const body = (await response.json().catch(() => null)) as { error?: { code?: string } } | null;
    throw new TelemetryApiError(body?.error?.code ?? "request_failed", response.status, "Analysis request failed");
  }
  return response.json() as Promise<T>;
}

function scoped(path: string, scope: AnalysisScope): string {
  return `${path}?${new URLSearchParams({ ...scope, limit: scope.limit ?? "200" })}`;
}

export const getAnomalies = (token: string, scope: AnalysisScope) => request<AnomalyListResponse>(scoped("/api/anomalies/v1/", scope), token);
export const getAnomaly = (token: string, id: string) => request<AnomalyDetailResponse>(`/api/anomalies/v1/${id}/?environment=local`, token);
export const getFaultExperiments = (token: string, scope: AnalysisScope) => request<FaultListResponse>(scoped("/api/fault-experiments/v1/", scope), token);
export const createFaultExperiment = (token: string, body: object) => request<FaultResponse>("/api/fault-experiments/v1/", token, { method: "POST", body: JSON.stringify(body) });
export const stopFaultExperiment = (token: string, id: string) => request<FaultResponse>(`/api/fault-experiments/v1/${id}/stop/`, token, { method: "POST", body: JSON.stringify({ environment: "local" }) });
export const repeatFaultExperiment = (token: string, id: string) => request<FaultResponse>(`/api/fault-experiments/v1/${id}/repeat/`, token, { method: "POST", body: JSON.stringify({ environment: "local" }) });
export const getModels = (token: string, scope: AnalysisScope) => request<ModelListResponse>(scoped("/api/models/v1/", scope), token);
export const getModelReadiness = (token: string, scope: AnalysisScope) => request<ModelReadinessResponse>(scoped("/api/models/v1/readiness/", scope), token);
export const trainModel = (token: string, body: object) => request<ModelResponse>("/api/models/v1/train/", token, { method: "POST", body: JSON.stringify(body) });
export const activateModel = (token: string, id: string) => request<ModelResponse>(`/api/models/v1/${id}/activate/`, token, { method: "POST", body: JSON.stringify({ environment: "local" }) });
export const trainLstmPrototype = (token: string, body: object) => request<LstmPrototypeResult>("/api/models/v1/lstm-prototype/train/", token, { method: "POST", body: JSON.stringify(body) });
export const getEvaluations = (token: string, scope: AnalysisScope) => request<EvaluationListResponse>(scoped("/api/evaluations/v1/", scope), token);
