import type { ActivityRow, AtRiskReport, Course, CourseStatus, User } from "../types";
import { ApiError, downloadFile, request } from "./client";

export async function listCoursesForUser(): Promise<Course[]> {
  return request<Course[]>("/courses");
}

export async function getCourse(id: string): Promise<Course | undefined> {
  try {
    return await request<Course>(`/courses/${id}`);
  } catch (error) {
    if (error instanceof ApiError && error.status === 404) return undefined;
    throw error;
  }
}

export async function listInstructors(courseId: string): Promise<User[]> {
  return request<User[]>(`/courses/${courseId}/instructors`);
}

export async function createCourse(input: Pick<Course, "code" | "title" | "term">): Promise<Course> {
  return request<Course>("/courses", { method: "POST", query: { role: "admin" }, json: input });
}

export async function setCoursePolicy(
  courseId: string,
  body: Pick<Course, "guardrailProfile" | "guardrailMode" | "aiAssist">,
): Promise<Course> {
  return request<Course>(`/courses/${courseId}/policy`, { method: "PATCH", query: { role: "admin" }, json: body });
}

export async function setCourseStatus(courseId: string, status: CourseStatus): Promise<Course> {
  return request<Course>(`/courses/${courseId}/status`, { method: "POST", query: { role: "admin" }, json: { status } });
}

export async function uploadGradingGuide(courseId: string, file: File): Promise<Course> {
  const formData = new FormData();
  formData.append("file", file);
  return request<Course>(`/courses/${courseId}/grading-guide`, { method: "POST", formData });
}

export function downloadGrades(courseId: string, role: string, caseKey: string): Promise<void> {
  return downloadFile(`/reports/courses/${courseId}/grades.xlsx`, "case-grades.xlsx", { role, case_key: caseKey });
}

export function getActivity(courseId: string, role: string, start: string, end: string): Promise<{ rows: ActivityRow[] }> {
  return request(`/reports/courses/${courseId}/activity`, { query: { role, start, end } });
}

export function getAtRisk(courseId: string, role: string): Promise<AtRiskReport> {
  return request(`/reports/courses/${courseId}/at-risk`, { query: { role } });
}

export function setInactivityDays(courseId: string, days: number): Promise<Course> {
  return request(`/courses/${courseId}/inactivity-days`, { method: "PATCH", json: { days } });
}

export function downloadChartTime(courseId: string, role: string, start: string, end: string): Promise<void> {
  return downloadFile(`/reports/courses/${courseId}/activity.xlsx`, "student-activity.xlsx", { role, start, end });
}

export function downloadAllActivity(start: string, end: string): Promise<void> {
  return downloadFile("/reports/activity.xlsx", "student-activity.xlsx", { start, end });
}
