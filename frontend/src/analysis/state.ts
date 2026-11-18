import type { FaultExperiment, Severity } from "./types";

export function severityLabel(severity: Severity): string {
  return { normal: "Normal", warning: "Uyarı", critical: "Kritik" }[severity];
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
