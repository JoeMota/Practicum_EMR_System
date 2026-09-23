import type { Appointment, Referral, User } from "../types";
import { USE_MOCK, apiFetch, clone, latency, uid } from "./client";
import { db } from "./mockDb";
import { recordAudit } from "./audit";

export async function listAppointments(patientId: string): Promise<Appointment[]> {
  if (!USE_MOCK) return apiFetch<Appointment[]>(`/patients/${patientId}/appointments`);
  await latency(120);
  return clone(db.appointments.filter((a) => a.patientId === patientId));
}

export async function listReferrals(patientId: string): Promise<Referral[]> {
  if (!USE_MOCK) return apiFetch<Referral[]>(`/patients/${patientId}/referrals`);
  await latency(120);
  return clone(db.referrals.filter((r) => r.patientId === patientId));
}

export async function createReferral(
  author: User, input: Omit<Referral, "id" | "createdByName" | "createdAt">,
): Promise<Referral> {
  if (!USE_MOCK) {
    return apiFetch<Referral>("/referrals", {
      method: "POST",
      body: {
        patientId: input.patientId,
        toDiscipline: input.toDiscipline,
        reason: input.reason,
        urgency: input.urgency,
      },
    });
  }
  await latency(200);
  const referral: Referral = { ...input, id: uid("rf"), createdByName: author.fullName, createdAt: new Date().toISOString() };
  db.referrals.unshift(referral);
  recordAudit(author, "referral.create", `patient/${input.patientId}`, "ok", `to ${input.toDiscipline}`);
  return clone(referral);
}
