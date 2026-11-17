import type { Role } from "../types";
import { request } from "./client";

export interface IntakeCondition {
  name: string;
  year: string;
}

export interface IntakeSurgery {
  procedure: string;
  year: string;
}

export interface IntakeAllergy {
  agent: string;
  reaction: string;
}

export interface IntakeMedication {
  name: string;
  dose: string;
  frequency: string;
}

export interface IntakeRelative {
  relative: "Mother" | "Father" | "Sibling" | "Grandparent" | "Child" | "Other";
  status: "" | "Living" | "Deceased" | "Unknown";
  conditions: string;
}

export interface IntakeData {
  preferredName: string;
  pronouns: string;
  genderIdentity: "" | "Woman" | "Man" | "Non-binary" | "Another" | "Prefer not to say";
  race: (
    | "American Indian or Alaska Native"
    | "Asian"
    | "Black or African American"
    | "Native Hawaiian or Other Pacific Islander"
    | "White"
    | "Another race"
    | "Prefer not to say"
  )[];
  ethnicity: "" | "Hispanic or Latino" | "Not Hispanic or Latino" | "Prefer not to say";
  maritalStatus: "" | "Single" | "Married" | "Partnered" | "Divorced" | "Separated" | "Widowed";
  interpreterNeeded: boolean;
  email: string;
  phone: string;
  phoneType: "" | "Mobile" | "Home" | "Work";
  address: string;
  city: string;
  state: string;
  zipCode: string;
  preferredLanguage: string;
  pastMedicalHistory: string;
  surgicalHistory: string;
  familyHistory: string;
  socialHistory: string;
  insurancePayer: string;
  insuranceMemberId: string;
  insuranceGroupNumber: string;
  insurancePlanType: "" | "HMO" | "PPO" | "EPO" | "POS" | "Medicare" | "Medicaid" | "Other";
  insuranceSubscriberIsPatient: boolean;
  insuranceSubscriberName: string;
  insuranceSubscriberDob: string | null;
  insuranceRelationship: "" | "Self" | "Spouse" | "Child" | "Other";
  insuranceEffectiveDate: string | null;
  secondaryInsurancePayer: string;
  secondaryInsuranceMemberId: string;
  secondaryInsuranceGroupNumber: string;
  secondaryInsuranceRelationship: "" | "Self" | "Spouse" | "Child" | "Other";
  conditions: IntakeCondition[];
  surgeries: IntakeSurgery[];
  allergies: IntakeAllergy[];
  noKnownAllergies: boolean;
  medications: IntakeMedication[];
  familyMembers: IntakeRelative[];
  tobaccoUse: "" | "Never" | "Former" | "Current";
  tobaccoDetail: string;
  alcoholUse: "" | "None" | "Occasional" | "Weekly" | "Daily";
  alcoholDetail: string;
  drugUse: "" | "Never" | "Former" | "Current";
  occupation: string;
  livesWith: string;
  exercise: string;
  emergencyContactName: string;
  emergencyContactPhone: string;
  emergencyContactRelationship: string;
  preferredPharmacy: string;
  confirmedAccurate: boolean;
}

export interface PortalIntake {
  data: IntakeData;
  identity: { firstName: string; lastName: string; dob: string; sexAtBirth: string; mrn: string };
  source: "chart" | "patient";
  updatedAt?: string | null;
  editable: boolean;
  notEditableReason?: string | null;
}

export interface StaffIntake {
  submitted: boolean;
  data?: IntakeData | null;
  updatedAt?: string | null;
}

export function emptyIntake(): IntakeData {
  return {
    preferredName: "",
    pronouns: "",
    genderIdentity: "",
    race: [],
    ethnicity: "",
    maritalStatus: "",
    interpreterNeeded: false,
    email: "",
    phone: "",
    phoneType: "",
    address: "",
    city: "",
    state: "",
    zipCode: "",
    preferredLanguage: "",
    pastMedicalHistory: "",
    surgicalHistory: "",
    familyHistory: "",
    socialHistory: "",
    insurancePayer: "",
    insuranceMemberId: "",
    insuranceGroupNumber: "",
    insurancePlanType: "",
    insuranceSubscriberIsPatient: true,
    insuranceSubscriberName: "",
    insuranceSubscriberDob: "",
    insuranceRelationship: "",
    insuranceEffectiveDate: "",
    secondaryInsurancePayer: "",
    secondaryInsuranceMemberId: "",
    secondaryInsuranceGroupNumber: "",
    secondaryInsuranceRelationship: "",
    conditions: [],
    surgeries: [],
    allergies: [],
    noKnownAllergies: false,
    medications: [],
    familyMembers: [],
    tobaccoUse: "",
    tobaccoDetail: "",
    alcoholUse: "",
    alcoholDetail: "",
    drugUse: "",
    occupation: "",
    livesWith: "",
    exercise: "",
    emergencyContactName: "",
    emergencyContactPhone: "",
    emergencyContactRelationship: "",
    preferredPharmacy: "",
    confirmedAccurate: false,
  };
}

export function getPortalIntake(): Promise<PortalIntake> {
  return request<PortalIntake>("/portal/intake", { query: { role: "patient" } });
}

export function savePortalIntake(data: IntakeData): Promise<PortalIntake> {
  return request<PortalIntake>("/portal/intake", { method: "PUT", query: { role: "patient" }, json: data });
}

export function getStaffIntake(patientId: string, role: Role): Promise<StaffIntake> {
  return request<StaffIntake>(`/patients/${patientId}/intake`, { query: { role } });
}
