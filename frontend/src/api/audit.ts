import type { AuditEntry, Role } from "../types";
import { request } from "./client";

export async function listAudit(courseId: string | undefined, role: Role): Promise<AuditEntry[]> {
  return request<AuditEntry[]>("/audit", { query: { course_id: courseId, role } });
}
