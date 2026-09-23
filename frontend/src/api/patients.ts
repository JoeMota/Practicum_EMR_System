import type { NoteStatus, Patient, PatientStatus, Role, User } from "../types";
import { can } from "../utils/permissions";
import { ApiError, USE_MOCK, apiFetch, clone, latency } from "./client";
import { db } from "./mockDb";
import { recordAudit } from "./audit";

export interface PatientRow {
  patient: Patient;
  ownerName?: string;
  latestNote?: { status: NoteStatus; updatedAt: string };
}

function visibleTo(p: Patient, viewer: User, role: Role): boolean {
  if (role === "student") return p.mode === "practice" || p.ownerId === viewer.id;
  return role === "instructor" || role === "admin" || role === "front_desk";
}

export async function listPatients(viewer: User, role: Role, courseId: string): Promise<PatientRow[]> {
  if (!USE_MOCK) {
    return apiFetch<PatientRow[]>(`/patients?courseId=${encodeURIComponent(courseId)}&role=${encodeURIComponent(role)}`);
  }
  await latency();
  return db.patients
    .filter((p) => p.courseId === courseId && visibleTo(p, viewer, role))
    .map((p) => {
      const authorId = role === "student" ? viewer.id : p.ownerId;
      const latest = db.notes
        .filter((n) => n.patientId === p.id && (!authorId || n.authorId === authorId))
        .sort((a, b) => b.updatedAt.localeCompare(a.updatedAt))[0];
      return {
        patient: clone(p),
        ownerName: db.users.find((u) => u.id === p.ownerId)?.fullName,
        latestNote: latest && { status: latest.status, updatedAt: latest.updatedAt },
      };
    });
}

export async function getPatient(viewer: User, role: Role, id: string): Promise<Patient> {
  if (!USE_MOCK) {
    return apiFetch<Patient>(`/patients/${id}?role=${encodeURIComponent(role)}`);
  }
  await latency();
  const p = db.patients.find((x) => x.id === id);
  if (!p) throw new ApiError(404, "This patient doesn't exist or was archived.");
  if (!visibleTo(p, viewer, role)) {
    recordAudit(viewer, "chart.view", `patient/${id}`, "denied", "Assessment case belongs to another student.");
    throw new ApiError(403, "This case belongs to another student. Each assessment case is private to the student it was assigned to.");
  }
  recordAudit(viewer, "chart.view", `patient/${id}`);
  const ownerName = role !== "student" ? db.users.find((u) => u.id === p.ownerId)?.fullName : undefined;
  return { ...clone(p), ownerName };
}

export async function updatePatientStatus(
  viewer: User, role: Role, id: string, patch: Partial<PatientStatus>,
): Promise<Patient> {
  if (!USE_MOCK) {
    return apiFetch<Patient>(`/patients/${id}/status?role=${encodeURIComponent(role)}`, {
      method: "PATCH",
      body: patch,
    });
  }
  await latency(150);
  const p = db.patients.find((x) => x.id === id);
  if (!p) throw new ApiError(404, "Patient not found.");
  const onlyEncounter = Object.keys(patch).every((k) => k === "encounter");
  const allowed = can(role, "patient:update_status") || (onlyEncounter && can(role, "encounter:advance"));
  if (!allowed) {
    recordAudit(viewer, "patient.update_status", `patient/${id}`, "denied");
    throw new ApiError(403, "Only instructors can change this status.");
  }
  p.status = { ...p.status, ...patch };
  recordAudit(viewer, "patient.update_status", `patient/${id}`, "ok", JSON.stringify(patch));
  return clone(p);
}

export async function resetPracticePatient(viewer: User, role: Role, id: string): Promise<void> {
  if (!USE_MOCK) {
    await apiFetch<void>(`/patients/${id}/reset`, { method: "POST" });
    return;
  }
  await latency(300);
  if (!can(role, "patient:reset_practice")) throw new ApiError(403, "Only instructors can reset practice patients.");
  const snapshot = db.practiceSnapshots.get(id);
  if (!snapshot) throw new ApiError(400, "Only practice patients can be reset.");
  const idx = db.patients.findIndex((p) => p.id === id);
  db.patients[idx] = structuredClone(snapshot);
  const [keep, archive] = [
    db.notes.filter((n) => n.patientId !== id),
    db.notes.filter((n) => n.patientId === id),
  ];
  db.notes.splice(0, db.notes.length, ...keep);
  db.archivedNotes.push(...archive);
  recordAudit(viewer, "patient.reset_practice", `patient/${id}`, "ok", `${archive.length} notes archived`);
}
