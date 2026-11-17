import type { IntakeData } from "../../api/intake";

const EMAIL = /^([^@\s]+@[^@\s]+\.[^@\s]+)?$/;
const PHONE = /^[0-9()+\-.\s]{0,40}$/;
const STATE = /^([A-Za-z]{2})?$/;
const ZIP = /^(\d{5}(-\d{4})?)?$/;
const YEAR = /^((19|20)\d{2})?$/;

function cleanRow<T extends Record<string, unknown>>(row: T): T {
  return Object.fromEntries(
    Object.entries(row).map(([key, value]) => [key, typeof value === "string" ? value.trim() : value]),
  ) as T;
}

function hasRowValue(row: object): boolean {
  return Object.values(row).some((value) => typeof value === "string" && value.trim() !== "");
}

export function toPayload(data: IntakeData): IntakeData {
  const cleaned = Object.fromEntries(
    Object.entries(data).map(([key, value]) => {
      if (typeof value === "string") return [key, value.trim()];
      if (Array.isArray(value)) {
        return [key, value.map((item) => typeof item === "string" ? item.trim() : cleanRow(item as Record<string, unknown>))];
      }
      return [key, value];
    }),
  ) as IntakeData;

  return {
    ...cleaned,
    insuranceSubscriberDob: cleaned.insuranceSubscriberDob || null,
    insuranceEffectiveDate: cleaned.insuranceEffectiveDate || null,
    conditions: cleaned.conditions.filter(hasRowValue),
    surgeries: cleaned.surgeries.filter(hasRowValue),
    allergies: cleaned.allergies.filter(hasRowValue),
    medications: cleaned.medications.filter(hasRowValue),
    familyMembers: cleaned.familyMembers.filter(hasRowValue),
  };
}

export function validateIntake(data: IntakeData): Record<string, string> {
  const errors: Record<string, string> = {};
  if (!EMAIL.test(data.email.trim())) errors.email = "Enter a valid email address.";
  if (!PHONE.test(data.phone.trim())) errors.phone = "Use a valid phone number.";
  if (!STATE.test(data.state.trim())) errors.state = "Enter a two-letter state code.";
  if (!ZIP.test(data.zipCode.trim())) errors.zipCode = "Enter a valid ZIP code.";
  data.conditions.forEach((item, index) => {
    if (!YEAR.test(item.year.trim())) errors[`conditions.${index}.year`] = "Enter a four-digit year.";
  });
  data.surgeries.forEach((item, index) => {
    if (!YEAR.test(item.year.trim())) errors[`surgeries.${index}.year`] = "Enter a four-digit year.";
  });
  return errors;
}

export function intakeCompleteness(data: IntakeData): { done: number; total: number; missing: string[] } {
  const hasText = (value: string) => value.trim().length > 0;
  const hasCondition = data.conditions.some((item) => hasText(item.name));
  const hasSurgery = data.surgeries.some((item) => hasText(item.procedure));
  const hasMedication = data.medications.some((item) => hasText(item.name));
  const hasAllergy = data.allergies.some((item) => hasText(item.agent));
  const hasFamilyHistory = data.familyMembers.some((item) => hasText(item.conditions));
  const checks: [string, boolean][] = [
    ["Preferred language", Boolean(data.preferredLanguage.trim())],
    ["Phone", Boolean(data.phone.trim())],
    ["Address", Boolean(data.address.trim() && data.city.trim() && data.state.trim() && data.zipCode.trim())],
    ["Email", Boolean(data.email.trim())],
    ["Primary insurance", Boolean(data.insurancePayer.trim() && data.insuranceMemberId.trim())],
    ["Emergency contact", Boolean(data.emergencyContactName.trim() && data.emergencyContactPhone.trim())],
    ["Health history", Boolean(hasCondition || hasSurgery || hasText(data.pastMedicalHistory) || hasMedication)],
    ["Allergies", Boolean(hasAllergy || data.noKnownAllergies)],
    ["Family history", Boolean(hasFamilyHistory || hasText(data.familyHistory))],
    ["Social history", Boolean(data.tobaccoUse && data.alcoholUse)],
    ["Review and confirm", data.confirmedAccurate],
  ];
  const missing = checks.filter(([, complete]) => !complete).map(([label]) => label);
  return { done: checks.length - missing.length, total: checks.length, missing };
}
