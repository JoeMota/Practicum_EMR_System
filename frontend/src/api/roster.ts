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
  reactivated: number;
  temporaryPasswords: TempPassword[];
}

export async function listRoster(courseId: string): Promise<User[]> {
  return request<User[]>(`/courses/${courseId}/roster`);
}

export async function importRoster(
  courseId: string, discipline: Discipline, rows: RosterRow[], role: "student" | "instructor" | "course_coordinator" = "student",
): Promise<RosterImportResult> {
  return request<RosterImportResult>(`/courses/${courseId}/roster/import`, {
    method: "POST",
    json: { discipline, rows, role },
  });
}

export { listInstructors };

export async function setRosterActive(courseId: string, userId: string, active: boolean): Promise<User> {
  const action = active ? "reactivate" : "deactivate";
  return request<User>(`/courses/${courseId}/roster/${userId}/${action}`, { method: "POST" });
}

export async function removeFromCourse(
  courseId: string, userId: string, role: "student" | "instructor" | "course_coordinator" = "student",
): Promise<void> {
  await request<void>(`/courses/${courseId}/roster/${userId}`, { method: "DELETE", query: { role } });
}

export async function enrollInCourse(
  courseId: string, userId: string, role: "student" | "instructor" | "course_coordinator", discipline: Discipline,
): Promise<User> {
  return request<User>(`/courses/${courseId}/enrollments`, {
    method: "POST",
    json: { userId, role, discipline },
  });
}
