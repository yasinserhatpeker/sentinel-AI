import { afterEach, describe, expect, it, vi } from "vitest";

import { demoServiceNames, runAllDemoServices, runDemoActivity, runDemoBatch } from "./demo-activity";

afterEach(() => vi.unstubAllGlobals());

describe("all-service demo activity", () => {
  it("starts a real batch for every demo service", async () => {
    const fetchMock = vi.fn(async (_path: string, init?: RequestInit) => new Response(
      JSON.stringify(init?.method === "POST" ? {} : []),
      { status: 200, headers: { "Content-Type": "application/json" } },
    ));
    vi.stubGlobal("fetch", fetchMock);

    const result = await runAllDemoServices(1);
    const postedCollections = fetchMock.mock.calls
      .filter(([, init]) => init?.method === "POST")
      .map(([path]) => path);

    expect(result.serviceCount).toBe(demoServiceNames.length);
    expect(result.requestedCount).toBe(demoServiceNames.length);
    expect(result.createdCount).toBe(demoServiceNames.length);
    expect(result.failedCount).toBe(0);
    expect(result.requestCount).toBe(demoServiceNames.length);
    expect(postedCollections).toEqual(expect.arrayContaining([
      "/demo/orders/v1/orders/",
      "/demo/inventory/v1/stock/",
      "/demo/payments/v1/authorizations/",
      "/demo/reporting/v1/reports/",
      "/demo/notifications/v1/notifications/",
    ]));
  });

  it("creates one record with exactly one HTTP request", async () => {
    const fetchMock = vi.fn(async (_path: string, _init?: RequestInit) => new Response(
      JSON.stringify({ reference: "order-1" }),
      { status: 201, headers: { "Content-Type": "application/json" } },
    ));
    vi.stubGlobal("fetch", fetchMock);

    const result = await runDemoActivity("orders-api", "create");

    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(fetchMock.mock.calls[0]?.[1]?.method).toBe("POST");
    expect(result).toMatchObject({ requestedCount: 1, createdCount: 1, failedCount: 0, requestCount: 1 });
  });

  it("reports actual batch successes instead of the requested count", async () => {
    let requestIndex = 0;
    vi.stubGlobal("fetch", vi.fn(async () => {
      requestIndex += 1;
      return requestIndex === 3
        ? new Response(JSON.stringify({ error: "failed" }), { status: 500, headers: { "Content-Type": "application/json" } })
        : new Response(JSON.stringify({}), { status: 201, headers: { "Content-Type": "application/json" } });
    }));

    const result = await runDemoBatch("orders-api", 5);

    expect(result).toEqual({ requestedCount: 5, createdCount: 4, failedCount: 1, requestCount: 5 });
  });
});
