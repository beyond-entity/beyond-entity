export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
  }
}
export const auth = () => {
  try {
    return JSON.parse(sessionStorage.getItem("tableq-device") || "null");
  } catch {
    return null;
  }
};
export async function api(
  url: string,
  body?: any,
  method = body === undefined ? "GET" : "POST",
  extra: Record<string, string> = {},
) {
  const d = auth(),
    headers: Record<string, string> = { ...extra };
  if (d?.token && !headers.Authorization && !url.startsWith("/api/customer"))
    headers.Authorization = "Bearer " + d.token;
  if (d?.unlock) headers["X-Tablet-Unlock"] = d.unlock;
  let requestKey = "";
  const pending = JSON.parse(
    sessionStorage.getItem("tableq-pending-http") || "{}",
  );
  if (body !== undefined) {
    headers["Content-Type"] = "application/json";
    const bytes = await crypto.subtle.digest(
      "SHA-256",
      new TextEncoder().encode(method + url + JSON.stringify(body)),
    );
    requestKey = Array.from(new Uint8Array(bytes))
      .map((x) => x.toString(16).padStart(2, "0"))
      .join("");
    headers["Idempotency-Key"] ||= pending[requestKey] || crypto.randomUUID();
    pending[requestKey] = headers["Idempotency-Key"];
    sessionStorage.setItem("tableq-pending-http", JSON.stringify(pending));
  }
  let last: any;
  for (let attempt = 0; attempt < 2; attempt++) {
    try {
      const res = await fetch(url, {
        method,
        headers,
        credentials: "same-origin",
        body: body === undefined ? undefined : JSON.stringify(body),
        signal: AbortSignal.timeout(15000),
      });
      const data = await res.json();
      if (res.status >= 500) {
        last = new ApiError(res.status, data.error || "Server unavailable");
        continue;
      }
      if (requestKey) {
        const current = JSON.parse(
          sessionStorage.getItem("tableq-pending-http") || "{}",
        );
        delete current[requestKey];
        sessionStorage.setItem("tableq-pending-http", JSON.stringify(current));
      }
      if (!res.ok)
        throw new ApiError(res.status, data.error || "Request failed");
      return data;
    } catch (e) {
      if (e instanceof ApiError && e.status < 500) throw e;
      last = e;
    }
  }
  throw last;
}
export const put = (url: string, body: any) => api(url, body, "PUT");
export async function location() {
  return new Promise<GeolocationPosition>((resolve, reject) =>
    navigator.geolocation.getCurrentPosition(resolve, reject, {
      enableHighAccuracy: true,
      maximumAge: 0,
      timeout: 10000,
    }),
  );
}
