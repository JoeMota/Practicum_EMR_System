import { request } from "./client";

export async function setUserActive(userId: string, isActive: boolean): Promise<void> {
  await request<void>(`/users/${userId}/active`, { method: "PATCH", json: { isActive } });
}