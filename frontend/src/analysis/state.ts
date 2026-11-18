import type { FaultExperiment, Severity } from "./types";

export function severityLabel(severity: Severity): string {
  return { normal: "Normal", warning: "Uyarı", critical: "Kritik" }[severity];
}

export function detectorLabel(detector: string): string {
  return ({
    static_threshold: "Static Threshold",
    median_mad: "Median/MAD",
    isolation_forest: "Isolation Forest",
  } as Record<string, string>)[detector] ?? detector.replaceAll("_", " ");
}

const featureLabels: Record<string, string> = {
  request_count: "Request count",
  error_rate: "Error rate",
  latency_p95_ms: "p95 latency",
  cpu_average: "Ortalama CPU",
  db_query_p95_ms: "Database query p95",
  queue_depth_max: "En yüksek Queue depth",
  queue_oldest_age_max_seconds: "En eski Queue işi",
};

export function evidenceLabel(field: string): string {
  return ({
    feature_id: "Feature kaydı",
    feature_schema_version: "Feature şeması",
    ...featureLabels,
  } as Record<string, string>)[field] ?? field.replaceAll("_", " ");
}

export function evidenceValue(field: string, value: number | string | null): string {
  if (value === null || value === undefined) return "Ölçülmedi";
  if (field === "error_rate" && typeof value === "number") return `${(value * 100).toFixed(2)}%`;
  if (["latency_p95_ms", "db_query_p95_ms"].includes(field) && typeof value === "number") return `${value.toFixed(1)} ms`;
  if (field === "cpu_average" && typeof value === "number") return `${value.toFixed(1)}%`;
  if (field === "queue_oldest_age_max_seconds" && typeof value === "number") return `${value.toFixed(0)} sn`;
  if (typeof value === "number") return Number.isInteger(value) ? value.toString() : value.toFixed(3);
  return value;
}

export function reasonLabel(reason: string): string {
  if (reason === "isolation_forest.outlier") return "Feature örüntüsü modelin normal çalışma alanının dışında kaldı.";
  if (reason === "median_mad.insufficient_history") return "Median/MAD için yeterli geçmiş window bulunmuyor.";
  if (reason === "median_mad.insufficient_observations") return "Karşılaştırılabilir metric gözlemi yetersiz.";
  const parts = reason.split(".");
  const field = parts.at(-2);
  const level = parts.at(-1);
  if (field) {
    const metric = featureLabels[field] ?? field.replaceAll("_", " ");
    if (level === "critical") return `${metric} kritik threshold değerini geçti.`;
    if (level === "warning") return `${metric} uyarı threshold değerini geçti.`;
    if (level === "high") return `${metric}, geçmiş Median/MAD dağılımına göre beklenenden yüksek.`;
  }
  return reason.replaceAll("_", " ");
}

export function faultRemainingSeconds(experiment: FaultExperiment, now = Date.now()): number | null {
  const deadline = experiment.status === "recovering" ? experiment.recovery_until : experiment.expires_at;
  if (!deadline || !["active", "recovering"].includes(experiment.status)) return null;
  return Math.max(0, Math.ceil((new Date(deadline).getTime() - now) / 1000));
}

export function activeFaults(experiments: FaultExperiment[], now = Date.now()): FaultExperiment[] {
  return experiments.filter((item) => {
    if (["pending", "active"].includes(item.status)) return true;
    if (item.status !== "recovering") return false;
    return faultRemainingSeconds(item, now) !== 0;
  });
}

export function percentage(value: number): string {
  return `${(value * 100).toFixed(1)}%`;
}

export function normalizedFaultDuration(value: unknown): number | null {
  if (value === "" || value === null || value === undefined) return null;
  const duration = Number(value);
  return Number.isInteger(duration) && duration >= 15 && duration <= 600 ? duration : null;
}
