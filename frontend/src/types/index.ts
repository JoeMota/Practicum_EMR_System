export type Discipline =
  | "pharmacy"
  | "physical_therapy"
  | "occupational_therapy"
  | "speech_language_pathology"
  | "nursing";

export type Role = "student" | "instructor" | "course_coordinator" | "admin" | "front_desk" | "patient";
export type CourseStatus = "planned" | "active" | "ended" | "archived";

export interface RoleAssignment {
  role: Role;
  discipline?: Discipline;
  courseIds: string[];
}

export interface User {
  id: string;
  fullName: string;
  email: string;
  universityId?: string;
  phoneLast4?: string;
  isActive: boolean;
  archivedAt?: string;
  roles: RoleAssignment[];
  rosterStatus?: "active" | "inactive";
  deactivatedAt?: string;
}

export interface ActivityRow {
  userId: string;
  student: string;
  lastSignIn?: string;
  sessions: number;
  activeMinutes: number;
  chartsOpened: number;
  notesStarted: number;
  notesSubmitted: number;
}

export interface AtRiskReport {
  days: number;
  students: { userId: string; student: string; reasons: string[] }[];
}

export interface Course {
  id: string;
  code: string;
  title: string;
  term: string;
  status: CourseStatus;
  inactivityDays?: number;
  instructorIds: string[];
  rubricFileName?: string;
  gradingGuide?: GradingGuide | null;
  guardrailProfile?: "intro_pharmacy" | "practicum" | "clinical_other";
  guardrailMode?: "off" | "advisory" | "acknowledge" | "block" | null;
  aiAssist?: boolean;
  aiProviderConfigured?: boolean;
}

export interface GradingCriterion {
  id: string;
  label: string;
  detail: string;
  max_points?: number | null;
}

export interface GradingGuide {
  file_name?: string | null;
  criteria: GradingCriterion[];
  source?: "case" | "course";
}

export interface PlantedTrigger {
  finding: string;
  explanation: string;
}

export interface RubricScores {
  criteria: { id: string; score?: number | null; feedback?: string; max_points?: number | null }[];
  overall_feedback?: string;
}

export type CaseMode = "practice" | "assessment" | "case" | "simulation";
export type SimulationPhase = "waiting_vitals" | "ready" | "closed";

export type LifecycleStatus =
  | "Active" | "Inactive" | "Prospective" | "Discharged from practice" | "Archived" | "Deceased";
export type EncounterStatus = "Scheduled" | "Checked in" | "Roomed" | "In progress" | "Checked out" | "Closed";
export type CareSetting = "Outpatient" | "Inpatient" | "Emergency" | "Discharged";

export interface PatientStatus {
  lifecycle: LifecycleStatus;
  encounter: EncounterStatus;
  careSetting: CareSetting;
  program?: string;
}

export type AllergyCategory = "medication" | "food" | "environmental";

export interface Allergy {
  id?: string;
  substance: string;
  reaction?: string;
  severity?: "mild" | "moderate" | "severe";
  category?: AllergyCategory;
}

export interface Medication {
  id: string;
  name: string;
  dose: string;
  route: string;
  frequency: string;
  sig?: string;
  indication?: string;
  adherence?: string;
  accessCost?: string;
  status?: "active" | "discontinued" | "entered_in_error";
  prescribed?: boolean;
  isCompound?: boolean;
  compoundIngredients?: string | null;
  compoundVehicle?: string | null;
  compoundReason?: string | null;
  discontinuedAt?: string;
  rxcui?: string;
  genericName?: string;
  brandNames?: string[];
  flags?: { code: string; message: string }[];
  acknowledgedFlags?: string[];
  clearFlags?: boolean;
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
  id?: string;
  label: string;
  value: string;
  recordedAt?: string;
  recordedByName?: string;
  status?: "recorded" | "entered_in_error";
}

export type LungSoundLocation = "RUL" | "RML" | "RLL" | "LUL" | "LLL";
export type LungSoundFinding = "clear" | "crackles" | "wheeze" | "diminished" | "rhonchi" | "other";

export interface LungSound {
  id?: string;
  location: LungSoundLocation | string;
  finding: LungSoundFinding | string;
  notes?: string | null;
  recordedAt?: string;
  recordedByName?: string;
  status?: "recorded" | "entered_in_error";
}

export interface Problem {
  id?: string;
  code?: string;
  description: string;
  since?: string;
}

export interface Encounter {
  id: string;
  type: string;
  date: string;
}

export interface Insurance {
  payer?: string | null;
  memberId?: string | null;
  groupNumber?: string | null;
  notes?: string | null;
}

export interface EmergencyContact {
  name?: string | null;
  phone?: string | null;
  relationship?: string | null;
}

export type CodeStatus = "Full code" | "DNR" | "DNI" | "Other";

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
  ownerId?: string;
  ownerName?: string;
  isTraining: true;
  practiceLabel?: string;
  chiefComplaint: string;
  hpi: string;
  pastMedicalHistory: string;
  status: PatientStatus;
  allergies: Allergy[];
  medications: Medication[];
  problems: Problem[];
  labs: LabResult[];
  vitals: Vital[];
  lungSounds?: LungSound[];
  familyHistory: string;
  surgicalHistory: string;
  socialHistory: string;
  encounter: Encounter;
  insurance?: Insurance;
  emergencyContact?: EmergencyContact;
  codeStatus?: CodeStatus | string | null;
  advanceDirectiveNotes?: string | null;
  hipaaOnFile?: boolean;
  hipaaSignedAt?: string | null;
  hipaaNote?: string | null;
  sectionLocks?: Record<string, boolean>;
  prefillSections?: string[];
  unit?: string;
  room?: string;
  bed?: string;
  hasPhoto?: boolean;
  simulationPhase?: SimulationPhase | null;
  viewerStation?: "nurse" | "pharmacist" | "provider" | null;
}

export type NoteStatus = "draft" | "signed" | "pending_review" | "returned" | "cosigned";

export type NoteTemplateId =
  | "pharmacy_soap"
  | "sbar"
  | "phone_note"
  | "telehealth_visit"
  | "pharmacy_mtm"
  | "pt_daily_soap"
  | "general_soap";

export interface IcdCode {
  code: string;
  label: string;
  rationale?: string;
}

export interface CptSelection extends IcdCode {
  diagnosisCodes: string[];
}

export interface NoteComment {
  id: string;
  authorId: string;
  authorName: string;
  body: string;
  kind: "returned" | "cosigned" | "comment";
  sectionId?: "S" | "O" | "MR" | "A" | "P";
  createdAt: string;
}

export interface Addendum {
  id: string;
  authorName: string;
  body: string;
  createdAt: string;
}

export interface AuthoredCase extends Patient {
  createdByName?: string;
  updatedAt: string;
  gradingGuide?: GradingGuide | null;
  triggers?: PlantedTrigger[];
}

export interface ClinicalNote {
  id: string;
  patientId: string;
  encounterId: string;
  templateId: string;
  authorId: string;
  authorName: string;
  authorDiscipline: Discipline;
  mode: CaseMode;
  kind?: "visit" | "clarification";
  status: NoteStatus;
  version: number;
  content: Record<string, string>;
  diagnoses: IcdCode[];
  cptCodes?: CptSelection[];
  bodyLocked?: boolean;
  rubricScores?: RubricScores | null;
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
  entity: string;
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
