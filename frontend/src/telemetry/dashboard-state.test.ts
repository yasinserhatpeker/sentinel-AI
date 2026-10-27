import { describe, expect, it } from "vitest";

import { dashboardState } from "./dashboard-state";
import type { TelemetryAggregateResponse } from "./types";

const fullResponse: TelemetryAggregateResponse = {
  schema_version: "telemetry.v1",
  scope: { environment: "local", service: "sentinel-demo-api", start: "2026-10-27T12:00:00Z", end: "2026-10-27T13:00:00Z" },
  availability: { http: true, runtime: true, database: true, queue: true },
  points: [{ timestamp: "2026-10-27T12:00:00Z", metric: "http.server.duration", unit: "ms", count: 1, minimum: 1, maximum: 1, average: 1, last: 1, p50: 1, p95: 1, p99: 1 }],
};

describe("dashboardState", () => {
  it("prioritises loading and errors over data", () => {
    expect(dashboardState({ loading: true, errorCode: "", services: [], response: null })).toBe("loading");
    expect(dashboardState({ loading: false, errorCode: "demo_token_invalid", services: [], response: null })).toBe("error");
  });

  it("distinguishes no services, no data, partial coverage and ready data", () => {
    expect(dashboardState({ loading: false, errorCode: "", services: [], response: null })).toBe("empty-services");
    expect(dashboardState({ loading: false, errorCode: "", services: ["sentinel-demo-api"], response: null })).toBe("empty-data");
    expect(dashboardState({ loading: false, errorCode: "", services: ["sentinel-demo-api"], response: { ...fullResponse, availability: { ...fullResponse.availability, queue: false } } })).toBe("partial");
    expect(dashboardState({ loading: false, errorCode: "", services: ["sentinel-demo-api"], response: fullResponse })).toBe("ready");
  });
});
