import type { ClinicalNote, CptSelection, Discipline, IcdCode, Patient, Role } from "../types";
import { request } from "./client";

export async function listNotesForPatient(role: Role, patientId: string): Promise<ClinicalNote[]> {
  return request<ClinicalNote[]>(`/patients/${patientId}/notes`, { query: { role } });
}

export function suggestSection(role: Role, noteId: string, sectionId: string): Promise<{ sectionId: string; suggestion: string }> {
  return request(`/notes/${noteId}/suggest`, { method: "POST", query: { role }, json: { sectionId } });
}

export function checkInsertedDose(
  role: Role, noteId: string, text: string, acknowledgedFlags: string[] = [],
): Promise<{ flags: { code: string; message: string }[]; blocked: boolean; needsAcknowledgement: boolean }> {
  return request(`/notes/${noteId}/dose-check`, {
    method: "POST",
    query: { role },
    json: { text, acknowledgedFlags },
  });
}

export async function getNote(role: Role, id: string): Promise<ClinicalNote> {
  return request<ClinicalNote>(`/notes/${id}`, { query: { role } });
}

export async function createDraft(
  discipline: Discipline, patient: Patient, templateId: string, role: Role, kind: "visit" | "clarification" = "visit",
): Promise<ClinicalNote> {
  return request<ClinicalNote>(`/patients/${patient.id}/notes`, {
    method: "POST",
    query: { role },
    json: { templateId, discipline, kind },
  });
}

export interface DraftPatch {
  templateId?: string;
  content?: Record<string, string>;
  diagnoses?: IcdCode[];
  cptCodes?: CptSelection[];
  routedToId?: string;
}

export async function saveDraft(id: string, expectedVersion: number, patch: DraftPatch, role: Role): Promise<ClinicalNote> {
  return request<ClinicalNote>(`/notes/${id}`, {
    method: "PATCH",
    query: { role },
    json: { expectedVersion, ...patch },
  });
}

export async function signNote(id: string, expectedVersion: number, role: Role): Promise<ClinicalNote> {
  return request<ClinicalNote>(`/notes/${id}/sign`, {
    method: "POST",
    query: { role },
    json: { expectedVersion },
  });
}

export async function cosignNote(role: Role, id: string, comment?: string): Promise<ClinicalNote> {
  return request<ClinicalNote>(`/notes/${id}/cosign`, {
    method: "POST",
    query: { role },
    json: { comment: comment ?? "" },
  });
}

export async function returnNote(role: Role, id: string, comment: string): Promise<ClinicalNote> {
  return request<ClinicalNote>(`/notes/${id}/return`, {
    method: "POST",
    query: { role },
    json: { comment },
  });
}

export async function commentOnNote(
  role: Role, id: string, body: { sectionId?: string; body: string },
): Promise<ClinicalNote> {
  return request<ClinicalNote>(`/notes/${id}/comments`, { method: "POST", query: { role }, json: body });
}

export async function instructorEditNote(role: Role, id: string, patch: DraftPatch): Promise<ClinicalNote> {
  return request<ClinicalNote>(`/notes/${id}/instructor-edit`, { method: "PATCH", query: { role }, json: patch });
}

export async function saveScores(
  role: Role,
  id: string,
  scores: { criteria: { id: string; score?: number | null; feedback: string; maxPoints?: number | null }[]; overallFeedback: string },
): Promise<ClinicalNote> {
  return request<ClinicalNote>(`/notes/${id}/scores`, { method: "PUT", query: { role }, json: scores });
}

export async function addAddendum(id: string, body: string, role: Role): Promise<ClinicalNote> {
  return request<ClinicalNote>(`/notes/${id}/addenda`, {
    method: "POST",
    query: { role },
    json: { body },
  });
}

export interface QueueItem {
  note: ClinicalNote;
  patient: Patient;
}

export async function listReviewQueue(courseId: string, role: Role): Promise<QueueItem[]> {
  return request<QueueItem[]>("/review-queue", { query: { course_id: courseId, role } });
}
