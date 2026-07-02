export type ApiResult<T> =
  | { ok: true; data: T }
  | { ok: false; error: string };

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000";

export async function apiGet<T>(path: string): Promise<ApiResult<T>> {
  return request<T>(path, { method: "GET" });
}

export async function apiPost<TRequest, TResponse>(
  path: string,
  body: TRequest,
): Promise<ApiResult<TResponse>> {
  return request<TResponse>(path, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(body),
  });
}

async function request<T>(path: string, init: RequestInit): Promise<ApiResult<T>> {
  try {
    const response = await fetch(`${API_BASE}${path}`, init);
    if (!response.ok) {
      return { ok: false, error: `HTTP ${response.status}` };
    }
    return { ok: true, data: (await response.json()) as T };
  } catch {
    return { ok: false, error: "backend_unavailable" };
  }
}
