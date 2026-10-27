export const demoServiceNames = [
  "orders-api",
  "inventory-api",
  "payments-api",
  "reporting-worker",
  "notifications-api",
] as const;

export const demoOperations = ["create-read", "update", "delete"] as const;

export type DemoServiceName = (typeof demoServiceNames)[number];
export type DemoOperation = (typeof demoOperations)[number];
type DomainRecord = Record<string, unknown>;

export class DemoActivityError extends Error {}

async function request<T = unknown>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, init);
  if (!response.ok) throw new DemoActivityError(`demo_request_failed_${response.status}`);
  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}

type ServiceActivity = {
  collection: string;
  payload: DomainRecord;
  detailPath: (created: DomainRecord) => string;
  update: DomainRecord;
};

function serviceActivity(service: DemoServiceName, suffix: string): ServiceActivity {
  switch (service) {
    case "orders-api":
      return { collection: "/demo/orders/v1/orders/", payload: { reference: `dashboard-order-${suffix}`, total: "42.50" }, detailPath: (item) => `/demo/orders/v1/orders/${encodeURIComponent(String(item.reference))}/`, update: { total: "49.90" } };
    case "inventory-api":
      return { collection: "/demo/inventory/v1/stock/", payload: { sku: `dashboard-sku-${suffix}`, available_quantity: 10 }, detailPath: (item) => `/demo/inventory/v1/stock/${encodeURIComponent(String(item.sku))}/`, update: { available_quantity: 7 } };
    case "payments-api":
      return { collection: "/demo/payments/v1/authorizations/", payload: { reference: `dashboard-auth-${suffix}`, order_reference: `dashboard-order-${suffix}`, amount: "42.50" }, detailPath: (item) => `/demo/payments/v1/authorizations/${encodeURIComponent(String(item.reference))}/`, update: { amount: "49.90" } };
    case "reporting-worker":
      return { collection: "/demo/reporting/v1/reports/", payload: { report_type: "dashboard-summary" }, detailPath: (item) => `/demo/reporting/v1/reports/${item.id}/`, update: { report_type: "dashboard-updated" } };
    case "notifications-api":
      return { collection: "/demo/notifications/v1/notifications/", payload: { recipient_reference: `dashboard-recipient-${suffix}`, channel: "email" }, detailPath: (item) => `/demo/notifications/v1/notifications/${item.id}/`, update: { channel: "sms" } };
  }
}

/** Runs real domain HTTP operations; it never constructs telemetry values. */
export async function runDemoActivity(service: DemoServiceName, operation: DemoOperation) {
  const activity = serviceActivity(service, `${Date.now()}-${Math.floor(Math.random() * 10_000)}`);
  const created = await request<DomainRecord>(activity.collection, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(activity.payload),
  });
  const detail = activity.detailPath(created);

  if (operation === "update") {
    await request<DomainRecord>(detail, { method: "PATCH", headers: { "Content-Type": "application/json" }, body: JSON.stringify(activity.update) });
    await request<DomainRecord>(detail);
    return { methods: "POST + PATCH + GET", recordCount: 1 };
  }
  if (operation === "delete") {
    await request<void>(detail, { method: "DELETE" });
    const records = await request<unknown[]>(activity.collection);
    return { methods: "POST + DELETE + GET", recordCount: records.length };
  }

  const records = await request<unknown[]>(activity.collection);
  return { methods: "POST + GET", recordCount: records.length };
}

/** Creates domain records through the service API so every request and queued job is real. */
export async function runDemoBatch(service: DemoServiceName, count = 10) {
  const concurrency = 10;
  for (let start = 0; start < count; start += concurrency) {
    const currentBatchSize = Math.min(concurrency, count - start);
    await Promise.all(Array.from({ length: currentBatchSize }, async () => {
      const activity = serviceActivity(service, `${Date.now()}-${Math.floor(Math.random() * 10_000_000)}`);
      await request<DomainRecord>(activity.collection, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(activity.payload),
      });
    }));
  }
  const activity = serviceActivity(service, `read-${Date.now()}`);
  const records = await request<unknown[]>(activity.collection);
  return { createdCount: count, recordCount: records.length };
}
