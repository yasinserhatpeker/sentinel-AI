import type { FaultExperiment, Severity } from "./types";

export function severityLabel(severity: Severity): string {
  return { normal: "Normal", warning: "Uyarı", critical: "Kritik" }[severity];
}

export function activeFaults(experiments: FaultExperiment[]): FaultExperiment[] {
  return experiments.filter((item) => ["pending", "active", "recovering"].includes(item.status));
}

export function percentage(value: number): string {
  return `${(value * 100).toFixed(1)}%`;
}
