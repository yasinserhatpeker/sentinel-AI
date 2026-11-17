import { describe, expect, it } from "vitest";
import { activeFaults, percentage, severityLabel } from "./state";
import type { FaultExperiment } from "./types";

const base = { id: "1", environment: "local", service: "orders-api", fault_type: "high_latency", parameters: {}, duration_seconds: 60, seed: 42, repeated_from: null, created_at: "2026-11-17T10:00:00Z", started_at: null, expires_at: null, stopped_at: null, recovery_until: null, failure_reason: null } as FaultExperiment;

describe("analysis view state", () => {
  it("keeps only operator-actionable fault states", () => {
    expect(activeFaults([{ ...base, status: "active" }, { ...base, id: "2", status: "completed" }, { ...base, id: "3", status: "recovering" }]).map((item) => item.id)).toEqual(["1", "3"]);
  });
  it("formats technical scores without changing their meaning", () => {
    expect(severityLabel("critical")).toBe("Kritik");
    expect(percentage(0.875)).toBe("87.5%");
  });
});
