import type { Discipline, NoteStatus, Role } from "../types";

export const disciplineLabel: Record<Discipline, string> = {
  pharmacy: "Pharmacy",
  physical_therapy: "Physical Therapy",
  occupational_therapy: "Occupational Therapy",
  speech_language_pathology: "Speech-Language Pathology",
  nursing: "Nursing",
};

export const roleLabel: Record<Role, string> = {
  student: "Student",
  instructor: "Instructor",
  course_coordinator: "Course coordinator",
  admin: "Administrator",
  front_desk: "Front desk",
  patient: "Patient",
};

export const noteStatusLabel: Record<NoteStatus, string> = {
  draft: "Draft",
  signed: "Signed",
  pending_review: "Needs review",
  returned: "Returned for revision",
  cosigned: "Co-signed",
};

export const noteStatusColor: Record<
  NoteStatus,
  "default" | "info" | "warning" | "error" | "success"
> = {
  draft: "default",
  signed: "success",
  pending_review: "warning",
  returned: "error",
  cosigned: "success",
};
