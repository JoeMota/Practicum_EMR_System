import type { Discipline, RosterRow, User } from "../types";
import { request } from "./client";
import { listInstructors } from "./courses";

export interface TempPassword {
  email: string;
  password: string;
}

export interface RosterImportResult {
  added: number;
  alreadyEnrolled: number;
  temporaryPasswords: TempPassword[];
}

export async function listRoster(courseId: string): Promise<User[]> {
  return request<User[]>(`/courses/${courseId}/roster`);
}

export async function importRoster(
  courseId: string, discipline: Discipline, rows: RosterRow[], role: "student" | "instructor" = "student",
): Promise<RosterImportResult> {
  return request<RosterImportResult>(`/courses/${courseId}/roster/import`, {
    method: "POST",
    json: { discipline, rows, role },
  });
}

export { listInstructors };

export async function removeFromCourse(courseId: string, userId: string, role: "student" | "instructor" = "student"): Promise<void> {
  await request<void>(`/courses/${courseId}/roster/${userId}`, { method: "DELETE", query: { role } });
}
