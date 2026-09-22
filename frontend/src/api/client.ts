// Shared HTTP helpers. Components import from api/* only — swap mock vs live here.

export const API_BASE = import.meta.env.VITE_API_URL
  ? `${String(import.meta.env.VITE_API_URL).replace(/\/$/, "")}/api/v1`
  : "/api/v1";

/** When true, api modules use in-memory mockDb instead of FastAPI. */
export const USE_MOCK = String(import.meta.env.VITE_USE_MOCK ?? "false").toLowerCase() === "true";

const TOKEN_KEY = "emr.access_token";

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

export function getAccessToken(): string | null {
  try {
    return sessionStorage.getItem(TOKEN_KEY);
  } catch {
    return null;
  }
}

export function setAccessToken(token: string | null) {
  try {
    if (token) sessionStorage.setItem(TOKEN_KEY, token);
    else sessionStorage.removeItem(TOKEN_KEY);
  } catch {
    /* ignore */
  }
}

export function latency(ms = 200): Promise<void> {
  return new Promise((r) => setTimeout(r, ms));
}

export function clone<T>(value: T): T {
  return structuredClone(value);
}

export function uid(prefix: string): string {
  return `${prefix}_${Math.random().toString(36).slice(2, 10)}`;
}

async function parseError(res: Response): Promise<ApiError> {
  let message = res.statusText || "Request failed";
  try {
    const data = await res.json();
    if (typeof data?.detail === "string") message = data.detail;
    else if (Array.isArray(data?.detail)) message = data.detail.map((d: { msg?: string }) => d.msg).filter(Boolean).join("; ") || message;
  } catch {
    /* ignore */
  }
  return new ApiError(res.status, message);
}

export interface RequestOptions extends Omit<RequestInit, "body"> {
  body?: unknown;
  auth?: boolean;
}

/** JSON fetch against the FastAPI backend. Attaches Bearer token by default. */
export async function apiFetch<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const { body, auth = true, headers: extra, ...rest } = options;
  const headers = new Headers(extra);
  if (body !== undefined && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }
  if (auth) {
    const token = getAccessToken();
    if (token) headers.set("Authorization", `Bearer ${token}`);
  }
  const res = await fetch(`${API_BASE}${path}`, {
    ...rest,
    headers,
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  if (!res.ok) throw await parseError(res);
  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}
