import type { AuditEntry, User } from "../types";
import { USE_MOCK, apiFetch, clone, latency, uid } from "./client";
import { db } from "./mockDb";

/** Append-only client-side audit for mock mode. Live API writes audit server-side. */
export function recordAudit(
  actor: Pick<User, "id" | "fullName">,
  action: string,
  entity: string,
  result: "ok" | "denied" = "ok",
  detail?: string,
) {
  if (!USE_MOCK) return;
  db.audit.unshift({
    id: uid("a"), timestamp: new Date().toISOString(),
    actorId: actor.id, actorName: actor.fullName, action, entity, result, detail,
  });
}

export async function listAudit(): Promise<AuditEntry[]> {
  if (!USE_MOCK) return apiFetch<AuditEntry[]>("/audit");
  await latency();
  return clone(db.audit);
}
