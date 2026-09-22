import type {
  Appointment, AuditEntry, ClinicalNote, Course, Patient, Referral, User,
} from "../types";

// Synthetic data only. Nothing here is a real person or real PHI.

const users: User[] = [
  {
    id: "u_daniel", fullName: "Daniel Reyes", email: "daniel.reyes@miners.utep.edu",
    universityId: "800123456", phoneLast4: "4412",
    roles: [{ role: "student", discipline: "pharmacy", courseIds: ["c_phar"] }],
  },
  {
    id: "u_clarissa", fullName: "Clarissa Dominguez", email: "clarissa.dominguez@miners.utep.edu",
    universityId: "800654321", phoneLast4: "9087",
    roles: [{ role: "student", discipline: "pharmacy", courseIds: ["c_phar"] }],
  },
  {
    id: "u_gerardo", fullName: "Gerardo Sillas", email: "gerardo.sillas@utep.edu", phoneLast4: "2260",
    roles: [
      { role: "instructor", courseIds: ["c_phar", "c_pt"] },
      { role: "admin", courseIds: ["c_phar", "c_pt"] },
    ],
  },
  {
    id: "u_chavez", fullName: "Joe Mota", email: "joe.mota@utep.edu", phoneLast4: "5521",
    roles: [{ role: "instructor", courseIds: ["c_phar"] }],
  },
  {
    id: "u_sam", fullName: "Sam Torres", email: "sam.torres@miners.utep.edu",
    universityId: "800999001", phoneLast4: "3344",
    roles: [{ role: "student", discipline: "pharmacy", courseIds: ["c_phar"] }],
  },
];

const courses: Course[] = [
  {
    id: "c_phar", code: "PHAR 5320", title: "Pharmacotherapy Skills Lab", term: "Fall 2026",
    instructorIds: ["u_gerardo", "u_chavez"], rubricFileName: "SOAP-note-rubric.pdf",
  },
  {
    id: "c_pt", code: "PHYT 6310", title: "Clinical Practice I", term: "Fall 2026",
    instructorIds: ["u_gerardo"], rubricFileName: "PT-daily-note-rubric.pdf",
  },
];

const today = "2026-09-22";

function t2dmCase(id: string, ownerId: string, suffix: string): Patient {
  // The client's example case, instantiated once per student (assessment mode).
  return {
    id, mrn: `TR-10057-${suffix}`, firstName: "Albert", lastName: "Einstein",
    dob: "1969-03-14", ageYears: 57, sexAtBirth: "Male", pronouns: "he/him",
    courseId: "c_phar", mode: "assessment", caseTemplateId: "case_t2dm", ownerId, isTraining: true,
    chiefComplaint: "Diabetes follow-up. \"My sugars have been running high.\"",
    hpi: "57-year-old male with type 2 diabetes diagnosed 10 years ago, on metformin 500 mg daily. Reports home fasting readings of 180–230 mg/dL for the past 2 months. Occasionally misses the dose. Denies hypoglycemia. Reports increased thirst.",
    status: { lifecycle: "Active", encounter: "Checked in", careSetting: "Outpatient" },
    allergies: [{ substance: "Penicillin", reaction: "Hives", severity: "moderate" }],
    medications: [
      { id: "m1", name: "Metformin", dose: "500 mg", route: "PO", frequency: "Once daily", indication: "Type 2 diabetes", adherence: "Misses ~2 doses/week" },
      { id: "m2", name: "Multivitamin", dose: "1 tablet", route: "PO", frequency: "Once daily", indication: "Supplement" },
    ],
    problems: [{ code: "E11.65", description: "Type 2 diabetes mellitus with hyperglycemia", since: "2016" }],
    labs: [
      { id: "l1", name: "Hemoglobin A1C", value: "10.5", unit: "%", referenceRange: "4.0–5.6", flag: "H", collectedAt: "2026-09-15" },
      { id: "l2", name: "Fasting glucose", value: "212", unit: "mg/dL", referenceRange: "70–99", flag: "H", collectedAt: "2026-09-15" },
      { id: "l3", name: "Serum creatinine", value: "0.9", unit: "mg/dL", referenceRange: "0.7–1.3", collectedAt: "2026-09-15" },
      { id: "l4", name: "eGFR", value: "92", unit: "mL/min/1.73m²", referenceRange: ">60", collectedAt: "2026-09-15" },
      { id: "l5", name: "Potassium", value: "4.2", unit: "mmol/L", referenceRange: "3.5–5.1", collectedAt: "2026-09-15" },
      { id: "l6", name: "LDL cholesterol", value: "96", unit: "mg/dL", referenceRange: "<100", collectedAt: "2026-09-15" },
    ],
    vitals: [
      { label: "BP", value: "138/86 mmHg" }, { label: "Pulse", value: "78 bpm" },
      { label: "SpO₂", value: "98%" }, { label: "Weight", value: "98 kg" },
      { label: "Height", value: "178 cm" }, { label: "BMI", value: "30.9" },
    ],
    familyHistory: "Mother: type 2 diabetes. Father: hypertension.",
    surgicalHistory: "Appendectomy (1990).",
    socialHistory: "Married. Never smoker. Alcohol 2 drinks/week. No drug use. Takes a daily multivitamin.",
    encounter: { id: `enc_${id}`, type: "Office visit", date: today },
  };
}

const patients: Patient[] = [
  {
    id: "p_pa", mrn: "TR-20001", firstName: "Rosa", lastName: "Villalobos", preferredName: "Rosie",
    dob: "1958-07-02", ageYears: 68, sexAtBirth: "Female", pronouns: "she/her",
    courseId: "c_phar", mode: "practice", caseTemplateId: "practice_a", isTraining: true,
    practiceLabel: "Test Patient A",
    chiefComplaint: "Blood pressure check and medication review.",
    hpi: "68-year-old female with hypertension here for a 3-month follow-up. Reports occasional ankle swelling in the evenings.",
    status: { lifecycle: "Active", encounter: "Checked in", careSetting: "Outpatient" },
    allergies: [{ substance: "Sulfa drugs", reaction: "Rash", severity: "mild" }],
    medications: [
      { id: "m1", name: "Lisinopril", dose: "10 mg", route: "PO", frequency: "Once daily", indication: "Hypertension" },
      { id: "m2", name: "Amlodipine", dose: "5 mg", route: "PO", frequency: "Once daily", indication: "Hypertension" },
    ],
    problems: [{ code: "I10", description: "Essential hypertension", since: "2012" }],
    labs: [
      { id: "l1", name: "Potassium", value: "4.6", unit: "mmol/L", referenceRange: "3.5–5.1", collectedAt: "2026-09-10" },
      { id: "l2", name: "Serum creatinine", value: "1.1", unit: "mg/dL", referenceRange: "0.6–1.1", collectedAt: "2026-09-10" },
    ],
    vitals: [
      { label: "BP", value: "146/88 mmHg" }, { label: "Pulse", value: "72 bpm" },
      { label: "SpO₂", value: "97%" }, { label: "Weight", value: "71 kg" },
    ],
    familyHistory: "Sister: stroke at 70.", surgicalHistory: "Cholecystectomy (2004).",
    socialHistory: "Widowed, lives alone. Former smoker, quit 2001.",
    encounter: { id: "enc_pa", type: "Office visit", date: today },
  },
  {
    id: "p_pb", mrn: "TR-20002", firstName: "Marcus", lastName: "Hill",
    dob: "1992-01-19", ageYears: 34, sexAtBirth: "Male",
    courseId: "c_pt", mode: "practice", caseTemplateId: "practice_b", isTraining: true,
    practiceLabel: "Test Patient B",
    chiefComplaint: "Right knee stiffness 6 weeks after ACL reconstruction.",
    hpi: "34-year-old male, 6 weeks post right ACL reconstruction. Pain 3/10 with stairs. Walking without crutches.",
    status: { lifecycle: "Active", encounter: "Scheduled", careSetting: "Outpatient", program: "Plan of care active" },
    allergies: [],
    medications: [
      { id: "m1", name: "Ibuprofen", dose: "400 mg", route: "PO", frequency: "Every 8 hours as needed", indication: "Knee pain" },
    ],
    problems: [{ description: "Status post right ACL reconstruction", since: "2026-08" }],
    labs: [],
    vitals: [{ label: "BP", value: "122/78 mmHg" }, { label: "Pulse", value: "64 bpm" }],
    familyHistory: "Noncontributory.", surgicalHistory: "Right ACL reconstruction (Aug 2026).",
    socialHistory: "Recreational soccer player. Office job.",
    encounter: { id: "enc_pb", type: "PT visit #4", date: today },
  },
  t2dmCase("p_ae_daniel", "u_daniel", "DR"),
  t2dmCase("p_ae_clarissa", "u_clarissa", "CD"),
  t2dmCase("p_ae_sam", "u_sam", "ST"),
];

const notes: ClinicalNote[] = [
  {
    id: "n_seed_sam", patientId: "p_ae_sam", encounterId: "enc_p_ae_sam", templateId: "pharmacy_mtm",
    authorId: "u_sam", authorName: "Sam Torres", authorDiscipline: "pharmacy", mode: "assessment",
    status: "pending_review", version: 4,
    content: {
      reason: "Diabetes follow-up, elevated home glucose.",
      med_experience: "Takes metformin in the morning, forgets ~2x/week. No cost issues.",
      objective: "A1C 10.5%, FBG 212, SCr 0.9, eGFR 92. BP 138/86.",
      dtp: "Needs additional therapy: A1C far above goal on metformin monotherapy at low dose. Adherence: missed doses.",
      rationale: "A1C >10% on low-dose metformin; renal function allows titration.",
      recommendations: "1. Increase metformin to 1000 mg twice daily over 4 weeks.\n2. Discuss adding a second agent.",
      followup: "Recheck A1C in 3 months.",
    },
    diagnoses: [{ code: "E11.65", label: "Type 2 diabetes mellitus with hyperglycemia" }],
    routedToId: "u_gerardo",
    createdAt: "2026-09-22T15:02:00", updatedAt: "2026-09-22T15:40:00", signedAt: "2026-09-22T15:40:00",
    feedback: [], addenda: [],
  },
];

const audit: AuditEntry[] = [
  { id: "a1", timestamp: "2026-09-22T15:02:11", actorId: "u_sam", actorName: "Sam Torres", action: "chart.view", entity: "patient/p_ae_sam", result: "ok" },
  { id: "a2", timestamp: "2026-09-22T15:40:02", actorId: "u_sam", actorName: "Sam Torres", action: "note.sign_submit", entity: "note/n_seed_sam", result: "ok" },
  { id: "a3", timestamp: "2026-09-22T15:41:30", actorId: "u_sam", actorName: "Sam Torres", action: "note.cosign", entity: "note/n_seed_sam", result: "denied", detail: "Students can author notes but cannot co-sign (403)." },
];

const appointments: Appointment[] = [
  { id: "ap1", patientId: "p_ae_daniel", when: "2026-12-15T09:30:00", kind: "Diabetes follow-up", withWhom: "Pharmacy clinic" },
  { id: "ap2", patientId: "p_pb", when: "2026-09-29T14:00:00", kind: "PT visit #5", withWhom: "Physical Therapy" },
];

const referrals: Referral[] = [];

export const db = {
  users,
  courses,
  patients,
  notes,
  audit,
  appointments,
  referrals,
  /** Original practice patients, so instructors can reset them for reuse. */
  practiceSnapshots: new Map(patients.filter((p) => p.mode === "practice").map((p) => [p.id, structuredClone(p)])),
  archivedNotes: [] as ClinicalNote[],
};
