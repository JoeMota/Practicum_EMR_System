import type { User } from "../types";
import { request } from "./client";
import type { TempPassword } from "./roster";

export async function updateAccount(userId: string, body: { fullName: string; email: string; universityId?: string }): Promise<User> {
  return request<User>(`/users/${userId}`, { method: "PATCH", json: body });
}

export async function setUserActive(userId: string, isActive: boolean): Promise<void> {
  await request<void>(`/users/${userId}/active`, { method: "PATCH", json: { isActive } });
}

export async function deleteAccount(userId: string, email: string): Promise<void> {
  await request(`/users/${userId}/delete`, { method: "POST", json: { email } });
}

export async function archiveUser(userId: string): Promise<void> {
  await request<void>(`/users/${userId}/archive`, { method: "POST" });
}

export async function purgeExpiredAccounts(): Promise<{ purged: number }> {
  return request<{ purged: number }>("/users/purge-expired", { method: "POST" });
}

export async function searchUsers(query: string): Promise<User[]> {
  return request<User[]>("/users", { query: { q: query } });
}

export async function resetPassword(userId: string): Promise<TempPassword> {
  return request<TempPassword>(`/users/${userId}/reset-password`, { method: "POST" });
}

export async function grantPortalAccess(body: { email: string; fullName: string; patientId: string }): Promise<{ temporaryPassword?: string }> {
  return request("/users/portal-access", { method: "POST", json: body });
}