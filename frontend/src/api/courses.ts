import type { Course, User } from "../types";
import { USE_MOCK, apiFetch, clone, latency } from "./client";
import { db } from "./mockDb";

export async function listCoursesForUser(user: User): Promise<Course[]> {
  if (!USE_MOCK) return apiFetch<Course[]>("/courses");
  await latency(150);
  const ids = new Set(user.roles.flatMap((r) => r.courseIds));
  return clone(db.courses.filter((c) => ids.has(c.id)));
}

export async function getCourse(id: string): Promise<Course | undefined> {
  if (!USE_MOCK) {
    try {
      return await apiFetch<Course>(`/courses/${id}`);
    } catch {
      return undefined;
    }
  }
  await latency(100);
  return clone(db.courses.find((c) => c.id === id));
}

export async function listInstructors(courseId: string): Promise<User[]> {
  if (!USE_MOCK) return apiFetch<User[]>(`/courses/${courseId}/instructors`);
  await latency(100);
  const course = db.courses.find((c) => c.id === courseId);
  return clone(db.users.filter((u) => course?.instructorIds.includes(u.id)));
}
