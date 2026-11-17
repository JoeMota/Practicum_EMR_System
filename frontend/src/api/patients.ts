import type { NoteStatus, Patient, PatientStatus, Role } from "../types";
import { request } from "./client";

export interface PatientRow {
  patient: Patient;
  ownerName?: string;
  latestNote?: { status: NoteStatus; updatedAt: string };
  openFlagCount?: number;
}

export async function listPatients(role: Role, courseId: string): Promise<PatientRow[]> {
  return request<PatientRow[]>("/patients", { query: { course_id: courseId, role } });
}

export async function getPatient(role: Role, id: string): Promise<Patient> {
  return request<Patient>(`/patients/${id}`, { query: { role } });
}

export interface PatientPhoto {
  contentType: string;
  data: string;
}

export function getPatientPhoto(role: Role, id: string): Promise<PatientPhoto> {
  return request<PatientPhoto>(`/patients/${id}/photo`, { query: { role } });
}

export function savePatientPhoto(role: Role, id: string, contentType: string, data: string): Promise<PatientPhoto> {
  return request<PatientPhoto>(`/patients/${id}/photo`, {
    method: "PUT",
    query: { role },
    json: { contentType, data },
  });
}

export async function updatePatientStatus(role: Role, id: string, patch: Partial<PatientStatus>): Promise<Patient> {
  return request<Patient>(`/patients/${id}/status`, { method: "PATCH", query: { role }, json: patch });
}

export async function resetPracticePatient(role: Role, id: string): Promise<void> {
  await request<void>(`/patients/${id}/reset`, { method: "POST", query: { role } });
}

export async function assignCase(
  role: Role, courseId: string, sourcePatientId: string, ownerId: string,
): Promise<Patient> {
  return request<Patient>("/patients", {
    method: "POST",
    query: { course_id: courseId, role },
    json: { sourcePatientId, ownerId },
  });
}

export async function unassignCase(role: Role, id: string): Promise<void> {
  await request<void>(`/patients/${id}`, { method: "DELETE", query: { role } });
}
