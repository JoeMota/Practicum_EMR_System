import type { Role, User } from "../types";

const origin = (import.meta.env.VITE_API_URL ?? "").replace(/\/$/, "");

export const API_BASE = `${origin}/api/v1`;

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

export const SESSION_KEY = "emr.session";
export const SESSION_EVENT = "emr:session";

export interface StoredSession {
  user: User;
  activeRole: Role;
  courseId?: string;
  accessToken: string;
  mustChangePassword: boolean;
}

export function readSession(): StoredSession | null {
  try {
    const raw = JSON.parse(sessionStorage.getItem(SESSION_KEY) ?? "null") as StoredSession | null;
    if (!raw?.accessToken || !raw.user || !raw.activeRole) return null;
    return raw;
  } catch {
    return null;
  }
}

export function writeSession(session: StoredSession | null, notify = true) {
  try {
    if (session) sessionStorage.setItem(SESSION_KEY, JSON.stringify(session));
    else sessionStorage.removeItem(SESSION_KEY);
  } catch {
    /* ignore quota / private mode */
  }
  if (notify) window.dispatchEvent(new Event(SESSION_EVENT));
}

export function tokenExpiresAt(token: string): number | null {
  try {
    const payload = token.split(".")[1];
    if (!payload) return null;
    const json = JSON.parse(atob(payload.replace(/-/g, "+").replace(/_/g, "/"))) as { exp?: number };
    return typeof json.exp === "number" ? json.exp * 1000 : null;
  } catch {
    return null;
  }
}

const NOTICE_KEY = "emr.signedOutReason";

export function setSignedOutNotice(message: string) {
  try {
    sessionStorage.setItem(NOTICE_KEY, message);
  } catch {
    /* ignore */
  }
}

export function takeSignedOutNotice(): string {
  try {
    const notice = sessionStorage.getItem(NOTICE_KEY) ?? "";
    if (notice) sessionStorage.removeItem(NOTICE_KEY);
    return notice;
  } catch {
    return "";
  }
}

let refreshing: Promise<string | null> | null = null;

export function refreshAccessToken(): Promise<string | null> {
  if (refreshing) return refreshing;
  refreshing = (async () => {
    const current = readSession();
    if (!current) return null;
    const res = await fetch(`${API_BASE}/auth/refresh`, {
      method: "POST",
      headers: { Authorization: `Bearer ${current.accessToken}` },
    });
    if (!res.ok) {
      writeSession(null);
      return null;
    }
    const body = (await res.json()) as {
      access_token: string;
      mustChangePassword: boolean;
      user: User;
    };
    const latest = readSession() ?? current;
    writeSession({
      ...latest,
      accessToken: body.access_token,
      mustChangePassword: body.mustChangePassword,
      user: body.user,
    });
    return body.access_token;
  })().finally(() => {
    refreshing = null;
  });
  return refreshing;
}

function queryString(query?: Record<string, string | number | undefined>): string {
  if (!query) return "";
  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(query)) {
    if (value !== undefined && value !== "") params.set(key, String(value));
  }
  const text = params.toString();
  return text ? `?${text}` : "";
}

async function errorMessage(res: Response): Promise<string> {
  const body = await res.json().catch(() => null) as { detail?: unknown } | null;
  const detail = body?.detail;
  if (typeof detail === "string" && detail.trim()) return detail;
  if (Array.isArray(detail)) {
    const messages = detail
      .map((item) => (item && typeof item === "object" && "msg" in item ? String(item.msg) : ""))
      .filter(Boolean);
    if (messages.length) return messages.join(" ");
  }
  return "Something went wrong. Try again.";
}

interface RequestOptions {
  method?: string;
  json?: unknown;
  form?: URLSearchParams;
  query?: Record<string, string | number | undefined>;
  auth?: boolean;
  responseType?: "json" | "text";
}

export async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const headers = new Headers();
  let body: BodyInit | undefined;
  if (options.json !== undefined) {
    headers.set("Content-Type", "application/json");
    body = JSON.stringify(options.json);
  } else if (options.form) {
    headers.set("Content-Type", "application/x-www-form-urlencoded");
    body = options.form;
  }

  if (options.auth !== false) {
    let token = readSession()?.accessToken ?? null;
    const exp = token ? tokenExpiresAt(token) : null;
    if (token && exp !== null && exp - Date.now() < 60_000) {
      token = await refreshAccessToken();
    }
    if (!token) {
      writeSession(null);
      throw new ApiError(401, "Your session expired. Sign in again.");
    }
    headers.set("Authorization", `Bearer ${token}`);
  }

  const res = await fetch(`${API_BASE}${path}${queryString(options.query)}`, {
    method: options.method ?? "GET",
    headers,
    body,
  });
  if (res.status === 401 && options.auth !== false) {
    writeSession(null);
    throw new ApiError(401, "Your session expired. Sign in again.");
  }
  if (!res.ok) throw new ApiError(res.status, await errorMessage(res));
  if (res.status === 204) return undefined as T;
  if (options.responseType === "text") return (await res.text()) as T;
  return (await res.json()) as T;
}
