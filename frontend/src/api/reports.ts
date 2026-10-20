import { request } from "./client";

export interface CourseReport {
  courseId: string;
  studentsEnrolled: number;
  notesByStatus: Record<string, number>;
  patientsByMode: Record<string, number>;
  auditEventCount: number;
  auditEventsByAction: Record<string, number>;
}

export async function getCourseReport(courseId: string): Promise<CourseReport> {
  return request<CourseReport>(`/reports/courses/${courseId}`);
}

export async function downloadCourseReport(courseId: string): Promise<string> {
  return request<string>(`/reports/courses/${courseId}`, { query: { format: "csv" }, responseType: "text" });
}