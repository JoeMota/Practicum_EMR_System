import type { User } from "../types";
import { ApiError, API_BASE, USE_MOCK, apiFetch, clone, latency, setAccessToken, uid } from "./client";
import { db } from "./mockDb";
import { recordAudit } from "./audit";

export type CodeChannel = "sms" | "email";

export interface AuthProviders {
  utepSso: boolean;
  duo: boolean;
  localMfa: boolean;
  requireUtepSso: boolean;
}

interface Challenge { userId: string; channel?: CodeChannel }
const challenges = new Map<string, Challenge>();

/** Dev-only code for mock + backend educational MFA. */
export const DEV_CODE = "123456";

const ALLOWED = /@(miners\.)?utep\.edu$/i;

export async function fetchAuthProviders(): Promise<AuthProviders> {
  if (USE_MOCK) {
    return { utepSso: false, duo: false, localMfa: true, requireUtepSso: false };
  }
  return apiFetch<AuthProviders>("/auth/providers", { auth: false });
}

/** Browser redirect into Microsoft Entra (UTEP campus login + Duo). */
export function startUtepSso(returnPath = "/auth/callback") {
  const base = API_BASE.replace(/\/$/, "");
  const url = `${base}/auth/sso/login?return_path=${encodeURIComponent(returnPath)}`;
  window.location.assign(url);
}

/** After Entra/Duo redirect, exchange the access token for a session user. */
export async function completeSsoSession(accessToken: string): Promise<User> {
  setAccessToken(accessToken);
  if (USE_MOCK) throw new ApiError(501, "SSO is for live API only");
  return apiFetch<User>("/auth/me");
}

export async function startSignIn(email: string, password: string) {
  if (!USE_MOCK) {
    return apiFetch<{
      challengeId?: string;
      phoneLast4?: string;
      emailMasked?: string;
      duoAuthUrl?: string;
    }>("/auth/challenge", {
      method: "POST",
      auth: false,
      body: { email, password },
    });
  }
  await latency(350);
  if (!ALLOWED.test(email.trim())) {
    throw new ApiError(400, "Use your UTEP email address (@utep.edu or @miners.utep.edu).");
  }
  const user = db.users.find((u) => u.email.toLowerCase() === email.trim().toLowerCase());
  if (!user || password.length === 0) {
    throw new ApiError(401, "That email and password don't match an EMR account. Ask your instructor to confirm you're on the course roster.");
  }
  const challengeId = uid("ch");
  challenges.set(challengeId, { userId: user.id });
  return {
    challengeId,
    phoneLast4: user.phoneLast4,
    emailMasked: user.email.replace(/^(.).*(@.*)$/, "$1•••$2"),
  };
}

export async function sendCode(challengeId: string, channel: CodeChannel) {
  if (!USE_MOCK) {
    await apiFetch<void>("/auth/send-code", {
      method: "POST",
      auth: false,
      body: { challengeId, channel },
    });
    return;
  }
  await latency(300);
  const ch = challenges.get(challengeId);
  if (!ch) throw new ApiError(410, "Your sign-in expired. Start again.");
  ch.channel = channel;
}

export async function verifyCode(challengeId: string, code: string): Promise<User> {
  if (!USE_MOCK) {
    const res = await apiFetch<{
      access_token: string;
      must_change_password: boolean;
      user: User;
    }>("/auth/verify-code", {
      method: "POST",
      auth: false,
      body: { challengeId, code },
    });
    setAccessToken(res.access_token);
    return {
      ...res.user,
      mustChangePassword: res.must_change_password || res.user.mustChangePassword,
    };
  }
  await latency(300);
  const ch = challenges.get(challengeId);
  if (!ch) throw new ApiError(410, "Your sign-in expired. Start again.");
  if (code !== DEV_CODE) throw new ApiError(401, "That code isn't right. Check the latest message and try again.");
  challenges.delete(challengeId);
  const user = db.users.find((u) => u.id === ch.userId)!;
  recordAudit(user, "auth.sign_in", `user/${user.id}`, "ok", `code via ${ch.channel ?? "sms"}`);
  return clone(user);
}

export async function changePassword(currentPassword: string, newPassword: string): Promise<void> {
  if (!USE_MOCK) {
    await apiFetch<void>("/auth/change-password", {
      method: "POST",
      body: { current_password: currentPassword, new_password: newPassword },
    });
    return;
  }
  await latency(200);
  if (newPassword.length < 8) throw new ApiError(400, "Password must be at least 8 characters.");
  if (currentPassword === newPassword) throw new ApiError(400, "New password must be different");
}

export async function fetchMe(): Promise<User> {
  if (USE_MOCK) throw new ApiError(501, "fetchMe is for live API only");
  return apiFetch<User>("/auth/me");
}

export function clearSessionToken() {
  setAccessToken(null);
}
