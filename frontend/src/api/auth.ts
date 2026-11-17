import type { User } from "../types";
import { ApiError, request } from "./client";

export interface LoginResult {
  accessToken: string;
  refreshToken?: string;
  mustChangePassword: boolean;
  user: User;
}

interface TokenResponse {
  access_token: string;
  refresh_token?: string;
  mustChangePassword: boolean;
  user: User;
}

export async function login(email: string, password: string): Promise<LoginResult> {
  const trimmed = email.trim();
  const form = new URLSearchParams();
  form.set("username", trimmed);
  form.set("password", password);
  try {
    const body = await request<TokenResponse>("/auth/login", { method: "POST", form, auth: false });
    return {
      accessToken: body.access_token,
      refreshToken: body.refresh_token,
      mustChangePassword: body.mustChangePassword,
      user: body.user,
    };
  } catch (error) {
    if (error instanceof ApiError && error.status === 401) {
      throw new ApiError(401, "That email and password don't match an active account.");
    }
    throw error;
  }
}

export async function logout(refreshToken: string): Promise<void> {
  await request<void>("/auth/logout", { method: "POST", json: { refreshToken }, auth: false });
}

export async function changePassword(currentPassword: string, newPassword: string): Promise<void> {
  await request<void>("/auth/change-password", {
    method: "POST",
    json: { currentPassword, newPassword },
  });
}

export async function setActingRole(role: string): Promise<LoginResult> {
  const body = await request<TokenResponse>("/auth/acting-role", {
    method: "POST",
    json: { role },
  });
  return {
    accessToken: body.access_token,
    refreshToken: body.refresh_token,
    mustChangePassword: body.mustChangePassword,
    user: body.user,
  };
}
