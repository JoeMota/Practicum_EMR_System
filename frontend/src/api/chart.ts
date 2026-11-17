import type { Allergy, LabResult, LungSound, Medication, Patient, Problem, Role, Vital } from "../types";
import { request } from "./client";

function chart(role: Role, patientId: string, path: string, method: string, json?: unknown) {
  return request<Patient>(`/patients/${patientId}${path}`, { method, query: { role }, json });
}

export function listOpened(role: Role, patientId: string): Promise<{ name: string; station?: string | null }[]> {
  return request(`/patients/${patientId}/opened`, { query: { role } });
}

export function recordPresence(role: Role, patientId: string): Promise<void> {
  return request<void>(`/patients/${patientId}/presence`, {
    method: "POST",
    query: { role },
    json: { active: true },
  });
}

export function addAllergy(role: Role, patientId: string, body: Omit<Allergy, "id">): Promise<Patient> {
  return chart(role, patientId, "/allergies", "POST", body);
}

export function removeAllergy(role: Role, patientId: string, allergyId: string): Promise<Patient> {
  return chart(role, patientId, `/allergies/${allergyId}`, "DELETE");
}

export function addMedication(role: Role, patientId: string, body: Omit<Medication, "id" | "status" | "discontinuedAt">): Promise<Patient> {
  return chart(role, patientId, "/medications", "POST", body);
}

export function updateMedication(
  role: Role, patientId: string, medicationId: string, body: Omit<Medication, "id" | "status" | "discontinuedAt">,
): Promise<Patient> {
  return chart(role, patientId, `/medications/${medicationId}`, "PATCH", body);
}

export function discontinueMedication(role: Role, patientId: string, medicationId: string): Promise<Patient> {
  return chart(role, patientId, `/medications/${medicationId}/discontinue`, "POST");
}

export function deleteMedicationEnteredInError(role: Role, patientId: string, medicationId: string): Promise<Patient> {
  return request<Patient>(`/patients/${patientId}/medications/${medicationId}`, {
    method: "DELETE",
    query: { role, reason: "entered_in_error" },
  });
}

export function administerMedication(role: Role, patientId: string, medicationId: string, doseGiven: string): Promise<{ status: string }> {
  return request(`/patients/${patientId}/medications/${medicationId}/administrations`, {
    method: "POST",
    query: { role },
    json: { doseGiven },
  });
}

export interface AdministrationRecord {
  id: string;
  medicationName: string;
  doseGiven: string;
  studentName: string;
  administeredAt: string;
  reviewStatus: string;
  reviewComment?: string | null;
}

export function listAdministrations(role: Role, patientId: string): Promise<AdministrationRecord[]> {
  return request<AdministrationRecord[]>(`/patients/${patientId}/administrations`, { query: { role } });
}

export function reviewAdministration(role: Role, administrationId: string, decision: "accepted" | "needs_follow_up", comment: string): Promise<void> {
  return request<void>(`/patients/administrations/${administrationId}/review`, {
    method: "POST",
    query: { role },
    json: { decision, comment },
  });
}

export interface MedicationOrderRecord {
  id: string;
  medicationId: string;
  name: string;
  dose: string;
  route: string;
  frequency: string;
  sig?: string | null;
  quantity?: string | null;
  status: "pending_verify" | "verified" | "released" | "held" | string;
  submittedByName: string;
  submittedAt: string;
  reviewedByName?: string | null;
  reviewedAt?: string | null;
  reviewComment?: string | null;
  isCompound?: boolean;
}

export function listMedicationOrders(role: Role, patientId: string): Promise<MedicationOrderRecord[]> {
  return request<MedicationOrderRecord[]>(`/patients/${patientId}/medication-orders`, { query: { role } });
}

export function submitMedicationOrder(role: Role, patientId: string, medicationId: string, quantity?: string): Promise<MedicationOrderRecord> {
  return request<MedicationOrderRecord>(`/patients/${patientId}/medication-orders`, {
    method: "POST",
    query: { role },
    json: { medicationId, quantity },
  });
}

export function reviewMedicationOrder(
  role: Role,
  orderId: string,
  decision: "verify" | "hold" | "release" | "resubmit",
  comment = "",
): Promise<MedicationOrderRecord> {
  return request<MedicationOrderRecord>(`/patients/medication-orders/${orderId}/review`, {
    method: "POST",
    query: { role },
    json: { decision, comment },
  });
}

export function addVital(role: Role, patientId: string, body: Pick<Vital, "label" | "value">): Promise<Patient> {
  return chart(role, patientId, "/vitals", "POST", body);
}

export function markVitalEnteredInError(role: Role, patientId: string, vitalId: string): Promise<Patient> {
  return chart(role, patientId, `/vitals/${vitalId}/entered-in-error`, "POST");
}

export function addLungSound(
  role: Role,
  patientId: string,
  body: Pick<LungSound, "location" | "finding" | "notes">,
): Promise<Patient> {
  return chart(role, patientId, "/lung-sounds", "POST", body);
}

export function markLungSoundEnteredInError(role: Role, patientId: string, lungSoundId: string): Promise<Patient> {
  return chart(role, patientId, `/lung-sounds/${lungSoundId}/entered-in-error`, "POST");
}

export function addLab(role: Role, patientId: string, body: Omit<LabResult, "id">): Promise<Patient> {
  return chart(role, patientId, "/labs", "POST", body);
}

export function addProblem(role: Role, patientId: string, body: Omit<Problem, "id">): Promise<Patient> {
  return chart(role, patientId, "/problems", "POST", body);
}

export function updatePlacement(role: Role, patientId: string, body: { unit?: string; room?: string; bed?: string }): Promise<Patient> {
  return chart(role, patientId, "/placement", "PATCH", body);
}
