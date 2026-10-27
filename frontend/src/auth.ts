let csrfToken = "";

function csrf(): string {
  return csrfToken || (document.cookie.split("; ").find((value) => value.startsWith("csrftoken="))?.split("=")[1] ?? "");
}

async function request(path: string, options: RequestInit = {}) {
  const response = await fetch(path, { credentials: "same-origin", ...options, headers: { "Content-Type": "application/json", "X-CSRFToken": csrf(), ...(options.headers ?? {}) } });
  if (!response.ok) throw new Error((await response.json().catch(() => null))?.error?.code ?? "request_failed");
  return response.status === 204 ? null : response.json();
}

export async function initialiseCsrf() {
  const response = await fetch("/api/auth/csrf/", { credentials: "same-origin" });
  const body = await response.json() as { csrfToken?: string };
  csrfToken = body.csrfToken ?? csrfToken;
}
export async function login(identifier: string, password: string): Promise<string> { await initialiseCsrf(); return (await request("/api/auth/login/", { method: "POST", body: JSON.stringify({ identifier, password }) })).access; }
export async function refresh(): Promise<string> { return (await request("/api/auth/refresh/", { method: "POST", body: "{}" })).access; }
export async function logout() { await request("/api/auth/logout/", { method: "POST", body: "{}" }); }
