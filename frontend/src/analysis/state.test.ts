import { describe, expect, it } from "vitest";
import { activeFaults, detectorLabel, evidenceLabel, evidenceValue, faultRemainingSeconds, normalizedFaultDuration, percentage, reasonLabel, severityLabel } from "./state";
import type { FaultExperiment } from "./types";

const base = { id: "1", environment: "local", service: "orders-api", fault_type: "high_latency", parameters: {}, duration_seconds: 60, seed: 42, repeated_from: null, created_at: "2026-11-17T10:00:00Z", started_at: null, expires_at: null, stopped_at: null, recovery_until: null, failure_reason: null } as FaultExperiment;

describe("analysis view state", () => {
  it("keeps only operator-actionable fault states", () => {
    const now = new Date("2026-11-17T10:00:00Z").getTime();
    expect(activeFaults([
      { ...base, status: "active" },
      { ...base, id: "2", status: "completed" },
      { ...base, id: "3", status: "recovering", recovery_until: "2026-11-17T10:02:00Z" },
      { ...base, id: "4", status: "recovering", recovery_until: "2026-11-17T09:59:00Z" },
    ], now).map((item) => item.id)).toEqual(["1", "3"]);
    expect(faultRemainingSeconds({ ...base, status: "recovering", recovery_until: "2026-11-17T10:02:00Z" }, now)).toBe(120);
  });
  it("formats technical scores without changing their meaning", () => {
    expect(severityLabel("critical")).toBe("Kritik");
    expect(percentage(0.875)).toBe("87.5%");
  });
  it("turns detector evidence into readable Turkish supporting copy", () => {
    expect(detectorLabel("median_mad")).toBe("Median/MAD");
    expect(evidenceLabel("latency_p95_ms")).toBe("p95 latency");
    expect(evidenceValue("latency_p95_ms", 123.456)).toBe("123.5 ms");
    expect(evidenceValue("error_rate", 0.125)).toBe("12.50%");
    expect(reasonLabel("median_mad.queue_depth_max.high")).toBe("En yüksek Queue depth, geçmiş Median/MAD dağılımına göre beklenenden yüksek.");
  });
  it("accepts only bounded whole-second fault durations", () => {
    expect(normalizedFaultDuration(15)).toBe(15);
    expect(normalizedFaultDuration("120")).toBe(120);
    expect(normalizedFaultDuration(600)).toBe(600);
    expect(normalizedFaultDuration(14)).toBeNull();
    expect(normalizedFaultDuration(60.5)).toBeNull();
    expect(normalizedFaultDuration("")).toBeNull();
  });
});
