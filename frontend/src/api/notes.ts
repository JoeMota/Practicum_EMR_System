import type { ClinicalNote, IcdCode, NoteTemplateId, Patient, Role, User } from "../types";
import { can } from "../utils/permissions";
import { ApiError, USE_MOCK, apiFetch, clone, latency, uid } from "./client";
import { db } from "./mockDb";
import { recordAudit } from "./audit";

const now = () => new Date().toISOString();

function find(id: string): ClinicalNote {
  const n = db.notes.find((x) => x.id === id);
  if (!n) throw new ApiError(404, "Note not found.");
  return n;
}

export async function listNotesForPatient(viewer: User, role: Role, patientId: string): Promise<ClinicalNote[]> {
  if (!USE_MOCK) {
    return apiFetch<ClinicalNote[]>(
      `/notes?patientId=${encodeURIComponent(patientId)}&role=${encodeURIComponent(role)}`,
    );
  }
  await latency(150);
  return clone(
    db.notes
      .filter((n) => n.patientId === patientId && (role !== "student" || n.authorId === viewer.id))
      .sort((a, b) => b.updatedAt.localeCompare(a.updatedAt)),
  );
}

export async function getNote(viewer: User, role: Role, id: string): Promise<ClinicalNote> {
  if (!USE_MOCK) {
    return apiFetch<ClinicalNote>(`/notes/${id}?role=${encodeURIComponent(role)}`);
  }
  await latency(150);
  const n = find(id);
  if (role === "student" && n.authorId !== viewer.id) {
    recordAudit(viewer, "note.view", `note/${id}`, "denied");
    throw new ApiError(403, "You can only open notes you wrote.");
  }
  recordAudit(viewer, "note.view", `note/${id}`);
  return clone(n);
}

export async function createDraft(
  author: User, discipline: ClinicalNote["authorDiscipline"], patient: Patient, templateId: NoteTemplateId,
): Promise<ClinicalNote> {
  if (!USE_MOCK) {
    return apiFetch<ClinicalNote>("/notes", {
      method: "POST",
      body: { patientId: patient.id, templateId, discipline },
    });
  }
  await latency(150);
  const note: ClinicalNote = {
    id: uid("n"), patientId: patient.id, encounterId: patient.encounter.id, templateId,
    authorId: author.id, authorName: author.fullName, authorDiscipline: discipline, mode: patient.mode,
    status: "draft", version: 1, content: {}, diagnoses: [],
    createdAt: now(), updatedAt: now(), feedback: [], addenda: [],
  };
  db.notes.unshift(note);
  recordAudit(author, "note.create", `note/${note.id}`);
  return clone(note);
}

export interface DraftPatch {
  templateId?: NoteTemplateId;
  content?: Record<string, string>;
  diagnoses?: IcdCode[];
  routedToId?: string;
}

export async function saveDraft(author: User, id: string, expectedVersion: number, patch: DraftPatch): Promise<ClinicalNote> {
  if (!USE_MOCK) {
    return apiFetch<ClinicalNote>(`/notes/${id}`, {
      method: "PATCH",
      body: { ...patch, expectedVersion },
    });
  }
  await latency(250);
  const n = find(id);
  if (n.authorId !== author.id) throw new ApiError(403, "Only the author can edit this note.");
  if (n.status !== "draft" && n.status !== "returned") throw new ApiError(409, "This note is signed. Add an addendum instead.");
  if (n.version !== expectedVersion) {
    throw new ApiError(409, "This note was changed in another window. Reload to see the latest version before editing.");
  }
  Object.assign(n, patch, { version: n.version + 1, updatedAt: now() });
  return clone(n);
}

export async function signNote(author: User, id: string, expectedVersion: number): Promise<ClinicalNote> {
  if (!USE_MOCK) {
    return apiFetch<ClinicalNote>(`/notes/${id}/sign`, {
      method: "POST",
      body: { expectedVersion },
    });
  }
  await latency(300);
  const n = find(id);
  if (n.authorId !== author.id) throw new ApiError(403, "Only the author can sign this note.");
  if (n.version !== expectedVersion) throw new ApiError(409, "This note changed in another window. Reload and try again.");
  if (n.mode === "assessment" && !n.routedToId) throw new ApiError(400, "Choose an instructor to review this note.");
  n.status = n.mode === "assessment" ? "pending_review" : "signed";
  n.signedAt = now();
  n.updatedAt = now();
  n.version += 1;
  recordAudit(author, n.mode === "assessment" ? "note.sign_submit" : "note.sign", `note/${id}`);
  return clone(n);
}

export async function cosignNote(reviewer: User, role: Role, id: string, comment?: string): Promise<ClinicalNote> {
  if (!USE_MOCK) {
    return apiFetch<ClinicalNote>(`/notes/${id}/cosign`, {
      method: "POST",
      body: { comment },
    });
  }
  await latency(300);
  const n = find(id);
  if (!can(role, "note:cosign")) {
    recordAudit(reviewer, "note.cosign", `note/${id}`, "denied", "Role lacks co-signature authority (403).");
    throw new ApiError(403, "Your role can't co-sign notes.");
  }
  if (n.status !== "pending_review") throw new ApiError(409, "Only notes pending review can be co-signed.");
  n.status = "cosigned";
  n.cosignedAt = now();
  n.cosignedByName = reviewer.fullName;
  n.updatedAt = now();
  n.version += 1;
  if (comment?.trim()) {
    n.feedback.push({ id: uid("c"), authorId: reviewer.id, authorName: reviewer.fullName, body: comment.trim(), kind: "cosigned", createdAt: now() });
  }
  recordAudit(reviewer, "note.cosign", `note/${id}`);
  return clone(n);
}

export async function returnNote(reviewer: User, role: Role, id: string, comment: string): Promise<ClinicalNote> {
  if (!USE_MOCK) {
    return apiFetch<ClinicalNote>(`/notes/${id}/return`, {
      method: "POST",
      body: { comment },
    });
  }
  await latency(300);
  const n = find(id);
  if (!can(role, "note:cosign")) throw new ApiError(403, "Your role can't return notes.");
  if (!comment.trim()) throw new ApiError(400, "Tell the student what to revise.");
  if (n.status !== "pending_review") throw new ApiError(409, "Only notes pending review can be returned.");
  n.status = "returned";
  n.updatedAt = now();
  n.version += 1;
  n.feedback.push({ id: uid("c"), authorId: reviewer.id, authorName: reviewer.fullName, body: comment.trim(), kind: "returned", createdAt: now() });
  recordAudit(reviewer, "note.return", `note/${id}`);
  return clone(n);
}

export async function addAddendum(author: User, id: string, body: string): Promise<ClinicalNote> {
  if (!USE_MOCK) {
    return apiFetch<ClinicalNote>(`/notes/${id}/addendum`, {
      method: "POST",
      body: { body },
    });
  }
  await latency(200);
  const n = find(id);
  if (n.status !== "signed" && n.status !== "cosigned") throw new ApiError(409, "Addenda are for signed notes. Edit the draft instead.");
  n.addenda.push({ id: uid("ad"), authorName: author.fullName, body: body.trim(), createdAt: now() });
  n.updatedAt = now();
  n.version += 1;
  recordAudit(author, "note.addendum", `note/${id}`);
  return clone(n);
}

export interface QueueItem {
  note: ClinicalNote;
  patient: Patient;
}

export async function listReviewQueue(reviewer: User, courseId: string): Promise<QueueItem[]> {
  if (!USE_MOCK) {
    return apiFetch<QueueItem[]>(`/notes/review-queue?courseId=${encodeURIComponent(courseId)}`);
  }
  await latency();
  return db.notes
    .filter((n) => n.mode === "assessment" && n.status !== "draft" && n.routedToId === reviewer.id)
    .map((n) => ({ note: clone(n), patient: clone(db.patients.find((p) => p.id === n.patientId)!) }))
    .filter((q) => q.patient && q.patient.courseId === courseId)
    .sort((a, b) => (b.note.signedAt ?? "").localeCompare(a.note.signedAt ?? ""));
}
