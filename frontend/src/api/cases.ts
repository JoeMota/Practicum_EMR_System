import type {
  Allergy, AuthoredCase, CareSetting, EncounterStatus, GradingGuide, LabResult, LifecycleStatus, LungSound, Medication, Patient, PlantedTrigger, Problem, Role, Vital,
} from "../types";
import { downloadFile, request } from "./client";

export interface CaseInput {
  firstName: string;
  lastName: string;
  preferredName?: string;
  dob: string;
  sexAtBirth: "Male" | "Female";
  pronouns?: string;
  chiefComplaint: string;
  hpi: string;
  pastMedicalHistory: string;
  surgicalHistory: string;
  familyHistory: string;
  socialHistory: string;
  insurancePayer?: string;
  insuranceMemberId?: string;
  insuranceGroupNumber?: string;
  insuranceNotes?: string;
  emergencyContactName?: string;
  emergencyContactPhone?: string;
  emergencyContactRelationship?: string;
  codeStatus?: string;
  advanceDirectiveNotes?: string;
  hipaaOnFile?: boolean;
  hipaaNote?: string;
  encounterType: string;
  careSetting: CareSetting;
  lifecycle: LifecycleStatus;
  encounterStatus: EncounterStatus;
  program?: string;
  allergies: Pick<Allergy, "substance" | "reaction" | "severity" | "category">[];
  medications: Omit<Medication, "id" | "status" | "discontinuedAt">[];
  sectionLocks?: Record<string, boolean>;
  prefillSections?: string[];
  unit?: string;
  room?: string;
  bed?: string;
  problems: Problem[];
  labs: Omit<LabResult, "id">[];
  vitals: Vital[];
  lungSounds?: Pick<LungSound, "location" | "finding" | "notes">[];
}

export async function listCases(role: Role, courseId: string): Promise<AuthoredCase[]> {
  return request<AuthoredCase[]>("/cases", { query: { course_id: courseId, role } });
}

export async function getCase(role: Role, id: string): Promise<AuthoredCase> {
  return request<AuthoredCase>(`/cases/${id}`, { query: { role } });
}

export async function createCase(role: Role, courseId: string, body: CaseInput): Promise<AuthoredCase> {
  return request<AuthoredCase>("/cases", { method: "POST", query: { course_id: courseId, role }, json: body });
}

export async function updateCase(role: Role, id: string, body: CaseInput): Promise<AuthoredCase> {
  return request<AuthoredCase>(`/cases/${id}`, { method: "PATCH", query: { role }, json: body });
}

export function downloadCaseTemplate(role: Role, courseId: string): Promise<void> {
  return downloadFile("/cases/import-template", "Patient_Case_Upload_Template.xlsx", { course_id: courseId, role });
}

export function importCases(role: Role, courseId: string, file: File): Promise<{ created: number }> {
  const formData = new FormData();
  formData.append("file", file);
  return request<{ created: number }>("/cases/import", { method: "POST", query: { course_id: courseId, role }, formData });
}

export interface AnswerDiagnosis {
  rank: number;
  code: string;
  label: string;
  rationale: string;
}

export interface AnswerKey {
  diagnoses: AnswerDiagnosis[];
  expectedCptCodes: { code: string; label: string }[];
  planPoints: string[];
  rationale: string;
  updatedAt?: string;
}

export async function getAnswerKey(role: Role, caseId: string): Promise<AnswerKey> {
  return request<AnswerKey>(`/cases/${caseId}/answer-key`, { query: { role } });
}

export async function getChartAnswerKey(role: Role, patientId: string): Promise<AnswerKey> {
  return request<AnswerKey>(`/patients/${patientId}/answer-key`, { query: { role } });
}

export async function releaseChartAnswerKey(role: Role, patientId: string): Promise<{ released: boolean; answerKeyReleasedAt?: string }> {
  return request(`/patients/${patientId}/answer-key/release`, { method: "POST", query: { role } });
}

export async function uploadCaseRubric(role: Role, caseId: string, file: File): Promise<GradingGuide> {
  const formData = new FormData();
  formData.append("file", file);
  return request<GradingGuide>(`/cases/${caseId}/rubric`, { method: "POST", query: { role }, formData });
}

export async function getChartGradingGuide(role: Role, patientId: string): Promise<GradingGuide> {
  return request<GradingGuide>(`/patients/${patientId}/grading-guide`, { query: { role } });
}

export async function putTriggers(role: Role, caseId: string, triggers: PlantedTrigger[]): Promise<{ triggers: PlantedTrigger[] }> {
  return request(`/cases/${caseId}/triggers`, { method: "PUT", query: { role }, json: { triggers } });
}

export async function getChartTriggers(role: Role, patientId: string): Promise<{ triggers: PlantedTrigger[] }> {
  return request(`/patients/${patientId}/triggers`, { query: { role } });
}

export async function startSimulation(
  role: Role, courseId: string, caseId: string,
  body: { nurseId: string; pharmacistId?: string; providerId?: string },
): Promise<Patient> {
  return request(`/cases/${caseId}/simulations`, { method: "POST", query: { course_id: courseId, role }, json: body });
}

export async function copyCase(role: Role, caseId: string, courseId: string): Promise<AuthoredCase> {
  return request<AuthoredCase>(`/cases/${caseId}/copy`, { method: "POST", query: { role }, json: { courseId } });
}

export async function putAnswerKey(
  role: Role,
  caseId: string,
  body: { diagnoses: AnswerDiagnosis[]; expectedCptCodes: { code: string; label: string }[]; planPoints: string[]; rationale: string },
): Promise<AnswerKey> {
  return request<AnswerKey>(`/cases/${caseId}/answer-key`, { method: "PUT", query: { role }, json: body });
}
