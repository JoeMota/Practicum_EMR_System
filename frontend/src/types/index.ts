// Domain types shared across features. These mirror the FastAPI schemas so
// swapping the mock API for real endpoints doesn't ripple through the UI.

export type Discipline =
  | "pharmacy"
  | "physical_therapy"
  | "occupational_therapy"
  | "speech_language_pathology"
  | "nursing";

/** A user can hold several roles (client: "Yes, a user can have more than one role"). */
export type Role = "student" | "instructor" | "admin" | "front_desk" | "patient";

export interface RoleAssignment {
  role: Role;
  discipline?: Discipline;
  courseIds: string[];
}

export interface User {
  id: string;
  fullName: string;
  email: string;
  universityId?: string; // 800 number
  phoneLast4?: string;
  roles: RoleAssignment[];
  /** FR-08: temp-password accounts must change before clinical screens. */
  mustChangePassword?: boolean;
}

export interface Course {
  id: string;
  code: string;
  title: string;
  term: string;
  instructorIds: string[];
  rubricFileName?: string;
}

/** Practice = shared, resettable, ungraded. Assessment = isolated copy per student, routed for review. */
export type CaseMode = "practice" | "assessment";

// Status is tracked across separate fields, never one dropdown.
export type LifecycleStatus =
  | "Active" | "Inactive" | "Prospective" | "Discharged from practice" | "Archived" | "Deceased";
export type EncounterStatus = "Scheduled" | "Checked in" | "In progress" | "Checked out" | "Closed";
export type CareSetting = "Outpatient" | "Inpatient" | "Emergency" | "Discharged";

export interface PatientStatus {
  lifecycle: LifecycleStatus;
  encounter: EncounterStatus;
  careSetting: CareSetting;
  program?: string;
}

export interface Allergy {
  substance: string;
  reaction?: string;
  severity?: "mild" | "moderate" | "severe";
}

export interface Medication {
  id: string;
  name: string;
  dose: string;
  route: string;
  frequency: string;
  indication?: string;
  adherence?: string;
}

export interface LabResult {
  id: string;
  name: string;
  value: string;
  unit: string;
  referenceRange: string;
  flag?: "H" | "L";
  collectedAt: string;
}

export interface Vital {
  label: string;
  value: string;
}

export interface Problem {
  code?: string;
  description: string;
  since?: string;
}

export interface Encounter {
  id: string;
  type: string;
  date: string;
}

export interface Patient {
  id: string;
  mrn: string;
  firstName: string;
  lastName: string;
  preferredName?: string;
  dob: string;
  ageYears: number;
  sexAtBirth: "Male" | "Female";
  pronouns?: string;
  courseId: string;
  mode: CaseMode;
  caseTemplateId: string;
  /** Set on assessment instances: the only student whose work appears on this copy. */
  ownerId?: string;
  /** Populated for instructors viewing an assessment instance. */
  ownerName?: string;
  isTraining: true;
  practiceLabel?: string; // "Test Patient A"
  chiefComplaint: string;
  hpi: string;
  status: PatientStatus;
  allergies: Allergy[];
  medications: Medication[];
  problems: Problem[];
  labs: LabResult[];
  vitals: Vital[];
  familyHistory: string;
  surgicalHistory: string;
  socialHistory: string;
  encounter: Encounter;
}

/**
 * draft          -> being written, editable by author
 * signed         -> practice-mode note signed by author, no review
 * pending_review -> signed by student, waiting on instructor
 * returned       -> instructor sent it back, editable again
 * cosigned       -> final; changes only via addendum
 */
export type NoteStatus = "draft" | "signed" | "pending_review" | "returned" | "cosigned";

export type NoteTemplateId = "pharmacy_mtm" | "pt_daily_soap" | "general_soap";

export interface IcdCode {
  code: string;
  label: string;
}

export interface NoteComment {
  id: string;
  authorId: string;
  authorName: string;
  body: string;
  kind: "returned" | "cosigned" | "comment";
  createdAt: string;
}

export interface Addendum {
  id: string;
  authorName: string;
  body: string;
  createdAt: string;
}

export interface ClinicalNote {
  id: string;
  patientId: string;
  encounterId: string;
  templateId: NoteTemplateId;
  authorId: string;
  authorName: string;
  authorDiscipline: Discipline;
  mode: CaseMode;
  status: NoteStatus;
  /** Optimistic-concurrency token. Saving with a stale version is rejected. */
  version: number;
  content: Record<string, string>;
  diagnoses: IcdCode[];
  routedToId?: string;
  createdAt: string;
  updatedAt: string;
  signedAt?: string;
  cosignedAt?: string;
  cosignedByName?: string;
  feedback: NoteComment[];
  addenda: Addendum[];
}

export interface AuditEntry {
  id: string;
  timestamp: string;
  actorId: string;
  actorName: string;
  action: string;
  actionLabel?: string;
  entity: string;
  recordLabel?: string;
  result: "ok" | "denied";
  detail?: string;
}

export interface Appointment {
  id: string;
  patientId: string;
  when: string;
  kind: string;
  withWhom: string;
}

export interface Referral {
  id: string;
  patientId: string;
  toDiscipline: Discipline;
  reason: string;
  urgency: "routine" | "urgent";
  createdByName: string;
  createdAt: string;
}

export interface RosterRow {
  fullName: string;
  email: string;
  universityId: string;
  problem?: string;
}
