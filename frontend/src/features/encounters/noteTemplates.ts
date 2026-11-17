import type { Discipline, NoteTemplateId, Patient } from "../../types";

export type FieldKind = "text" | "textarea" | "icd10" | "medrec";

export interface TemplateField {
  id: string;
  label: string;
  kind: FieldKind;
  required?: boolean; // Unused. Submit for signature is available before every section is filled in.
  placeholder?: string;
  rows?: number;
}

export interface TemplateSection {
  id: string;
  title: string;
  fields: TemplateField[];
}

export interface NoteTemplate {
  id: string;
  name: string;
  disciplines: Discipline[] | "all";
  sections: TemplateSection[];
}

const pharmacyMtm: NoteTemplate = {
  id: "pharmacy_mtm",
  name: "Comprehensive medication review (MTM)",
  disciplines: ["pharmacy"],
  sections: [
    {
      id: "S", title: "Subjective",
      fields: [
        { id: "reason", label: "Reason for visit / chief complaint", kind: "textarea", rows: 2, placeholder: "In the patient's words where possible" },
        { id: "med_experience", label: "Medication experience", kind: "textarea", rows: 3, placeholder: "How each medication is taken, missed doses, side effects, cost or access problems" },
      ],
    },
    {
      id: "O", title: "Objective",
      fields: [{ id: "objective", label: "Pertinent vitals and labs", kind: "textarea", rows: 3, placeholder: "Include values that drive your assessment, e.g. A1C, SCr/eGFR, BP" }],
    },
    {
      id: "MR", title: "Medication reconciliation",
      fields: [{ id: "medrec", label: "Reconciled medication list", kind: "medrec" }],
    },
    {
      id: "A", title: "Assessment",
      fields: [
        { id: "dx", label: "Diagnoses (ICD-10)", kind: "icd10",  },
        { id: "dtp", label: "Drug therapy problems", kind: "textarea", rows: 3, placeholder: "Indication, effectiveness, safety, adherence" },
        { id: "rationale", label: "Clinical rationale", kind: "textarea", rows: 3, placeholder: "What the data supports and why" },
      ],
    },
    {
      id: "P", title: "Plan",
      fields: [
        { id: "recommendations", label: "Pharmacist recommendations", kind: "textarea", rows: 4, placeholder: "One numbered item per drug therapy problem" },
        { id: "monitoring", label: "Monitoring", kind: "textarea", rows: 2, placeholder: "Parameters, targets, and when to check them" },
        { id: "education", label: "Patient education", kind: "textarea", rows: 2 },
        { id: "followup", label: "Follow-up and referrals", kind: "textarea", rows: 2 },
      ],
    },
  ],
};

const ptDaily: NoteTemplate = {
  id: "pt_daily_soap",
  name: "PT daily note (SOAP)",
  disciplines: ["physical_therapy"],
  sections: [
    {
      id: "S", title: "Subjective",
      fields: [
        { id: "visit_number", label: "Visit number", kind: "text" },
        { id: "subjective", label: "Patient report", kind: "textarea", rows: 3, placeholder: "Pain rating, function since last visit, home program adherence" },
      ],
    },
    {
      id: "O", title: "Objective",
      fields: [
        { id: "measures", label: "Measures", kind: "textarea", rows: 3, placeholder: "ROM, strength (MMT), gait, special tests" },
        { id: "interventions", label: "Interventions performed", kind: "textarea", rows: 3, placeholder: "Exercise, manual therapy, modalities, with parameters" },
      ],
    },
    {
      id: "A", title: "Assessment",
      fields: [
        { id: "dx", label: "Diagnoses (ICD-10)", kind: "icd10",  },
        { id: "progress", label: "Progress toward goals", kind: "textarea", rows: 3 },
      ],
    },
    {
      id: "P", title: "Plan",
      fields: [
        { id: "plan", label: "Plan", kind: "textarea", rows: 3, placeholder: "Next visit focus, frequency, home program changes" },
        { id: "goals", label: "Goal status", kind: "textarea", rows: 2, placeholder: "Met / progressing / not met for each goal" },
      ],
    },
  ],
};

const generalSoap: NoteTemplate = {
  id: "general_soap",
  name: "General encounter note (SOAP)",
  disciplines: "all",
  sections: [
    {
      id: "S", title: "Subjective",
      fields: [
        { id: "cc", label: "Chief complaint", kind: "text",  },
        { id: "hpi", label: "History of present illness", kind: "textarea", rows: 4, placeholder: "OLDCARTS: onset, location, duration, character, aggravating/relieving, radiation, timing, severity" },
        { id: "history", label: "PMH, PSH, medications, allergies, FH, SH", kind: "textarea", rows: 3 },
        { id: "ros", label: "Review of systems", kind: "textarea", rows: 3 },
      ],
    },
    {
      id: "O", title: "Objective",
      fields: [{ id: "exam", label: "Vitals and physical exam", kind: "textarea", rows: 4, placeholder: "By system" }],
    },
    {
      id: "A", title: "Assessment",
      fields: [
        { id: "dx", label: "Problem list (ICD-10)", kind: "icd10" },
      ],
    },
    {
      id: "P", title: "Plan",
      fields: [
        { id: "plan", label: "Plan by problem", kind: "textarea", rows: 4 },
        { id: "disposition", label: "Disposition", kind: "textarea", rows: 2 },
      ],
    },
  ],
};

const pharmacySoap: NoteTemplate = {
  id: "pharmacy_soap",
  name: "Pharmacy SOAP note",
  disciplines: ["pharmacy"],
  sections: [
    { id: "S", title: "Subjective", fields: [{ id: "subjective", label: "Subjective", kind: "textarea", rows: 6, placeholder: "What the patient reports, adherence, and home readings" }] },
    { id: "O", title: "Objective", fields: [{ id: "objective", label: "Objective", kind: "textarea", rows: 4, placeholder: "Vitals, labs, and current medications" }] },
    { id: "A", title: "Assessment", fields: [{ id: "assessment", label: "Assessment", kind: "textarea", rows: 5, placeholder: "Problem, goal, and why" }] },
    { id: "P", title: "Plan", fields: [{ id: "plan", label: "Plan", kind: "textarea", rows: 6, placeholder: "Numbered recommendations, monitoring, and follow-up" }] },
  ],
};

const sbar: NoteTemplate = {
  id: "sbar",
  name: "SBAR",
  disciplines: ["pharmacy"],
  sections: [
    { id: "S", title: "Situation", fields: [{ id: "situation", label: "Situation", kind: "textarea", rows: 3 }] },
    { id: "B", title: "Background", fields: [{ id: "background", label: "Background", kind: "textarea", rows: 3 }] },
    { id: "A", title: "Assessment", fields: [{ id: "assessment", label: "Assessment", kind: "textarea", rows: 4 }] },
    { id: "R", title: "Recommendation", fields: [{ id: "recommendation", label: "Recommendation", kind: "textarea", rows: 4 }] },
  ],
};

const phoneNote: NoteTemplate = {
  id: "phone_note",
  name: "Phone note",
  disciplines: "all",
  sections: [
    { id: "N", title: "Phone note", fields: [{ id: "account", label: "What happened", kind: "textarea", rows: 6, placeholder: "A brief account of the call" }] },
  ],
};

const telehealth: NoteTemplate = {
  id: "telehealth_visit",
  name: "Telehealth visit note",
  disciplines: "all",
  sections: [
    { id: "S", title: "Subjective", fields: [{ id: "subjective", label: "Subjective", kind: "textarea", rows: 4 }] },
    { id: "O", title: "Objective", fields: [{ id: "objective", label: "Objective", kind: "textarea", rows: 3, placeholder: "What could be assessed over video or phone" }] },
    { id: "A", title: "Assessment", fields: [{ id: "assessment", label: "Assessment", kind: "textarea", rows: 4 }] },
    { id: "P", title: "Plan", fields: [{ id: "plan", label: "Plan", kind: "textarea", rows: 4 }] },
  ],
};

export const TEMPLATES: Record<NoteTemplateId, NoteTemplate> = {
  pharmacy_soap: pharmacySoap,
  sbar,
  phone_note: phoneNote,
  telehealth_visit: telehealth,
  pharmacy_mtm: pharmacyMtm,
  pt_daily_soap: ptDaily,
  general_soap: generalSoap,
};

export function templatesFor(discipline?: Discipline): NoteTemplate[] {
  return Object.values(TEMPLATES).filter(
    (t) => t.disciplines === "all" || (discipline && t.disciplines.includes(discipline)),
  );
}

export function templateName(id?: string): string {
  if (id && id in TEMPLATES) return TEMPLATES[id as NoteTemplateId].name;
  return "Clinical note";
}

export function defaultTemplateFor(discipline?: Discipline): NoteTemplateId {
  if (discipline === "pharmacy") return "pharmacy_soap";
  if (discipline === "physical_therapy") return "pt_daily_soap";
  return "general_soap";
}

export function missingRequired(): string[] {
  return [];
}

function vitalsBlock(patient: Patient): string {
  const vitals = patient.vitals.filter((v) => v.status !== "entered_in_error");
  if (!vitals.length) return "";
  return vitals.map((v) => `${v.label}: ${v.value}`).join("; ");
}

function labsBlock(patient: Patient): string {
  if (!patient.labs.length) return "";
  return patient.labs
    .map((l) => `${l.name} ${l.value} ${l.unit}${l.flag ? ` (${l.flag})` : ""}`)
    .join("; ");
}

function historyBlock(patient: Patient): string {
  const allergy = patient.allergies.length
    ? patient.allergies.map((a) => `${a.substance}${a.reaction ? ` (${a.reaction})` : ""}`).join("; ")
    : "NKDA";
  const meds = patient.medications.map((m) => `${m.name} ${m.dose} ${m.route} ${m.frequency}`).join("; ") || "None listed";
  return [
    `PMH: ${patient.problems.map((p) => p.description).join("; ") || "None listed"}`,
    `PSH: ${patient.surgicalHistory}`,
    `Medications: ${meds}`,
    `Allergies: ${allergy}`,
    `FH: ${patient.familyHistory}`,
    `SH: ${patient.socialHistory}`,
  ].join("\n");
}

/**
 * Prefill a new note from the chart (DOC-02): chief complaint, vitals/labs, and
 * history blocks so students start from the encounter instead of a blank form.
 * Only fills fields the template actually has.
 */
export function prefillFromPatient(templateId: string, patient: Patient, template?: NoteTemplate): Record<string, string> {
  const enabled = new Set(patient.prefillSections ?? []);
  if (enabled.size === 0) return {};
  const chosen = template ?? (templateId in TEMPLATES ? TEMPLATES[templateId as NoteTemplateId] : undefined);
  if (!chosen) return {};
  const fieldIds = new Set(chosen.sections.flatMap((s) => s.fields.map((f) => f.id)));
  const vitals = vitalsBlock(patient);
  const labs = labsBlock(patient);
  const draft: Record<string, string> = {};

  const put = (id: string, value: string) => {
    if (fieldIds.has(id) && value.trim()) draft[id] = value.trim();
  };

  if (enabled.has("chief_complaint")) {
    put("reason", patient.chiefComplaint);
    put("cc", patient.chiefComplaint);
    put("subjective", patient.chiefComplaint);
    put("situation", patient.chiefComplaint);
    put("account", patient.chiefComplaint);
  }
  if (enabled.has("hpi")) {
    put("hpi", patient.hpi);
    put("background", patient.hpi);
  }
  if (enabled.has("vitals") || enabled.has("labs")) {
    const picked = [enabled.has("vitals") ? vitals : "", enabled.has("labs") ? labs : ""].filter(Boolean).join(". ");
    put("objective", picked);
    put("exam", picked);
    put("measures", picked);
  }
  if (enabled.has("history")) put("history", historyBlock(patient));

  return draft;
}

/** Seed ICD picks from the chart problem list when codes are present. */
export function diagnosesFromPatient(patient: Patient): { code: string; label: string }[] {
  if (!(patient.prefillSections ?? []).includes("diagnoses")) return [];
  const out: { code: string; label: string }[] = [];
  const seen = new Set<string>();
  for (const problem of patient.problems) {
    const code = problem.code?.trim();
    if (!code || seen.has(code)) continue;
    seen.add(code);
    out.push({ code, label: problem.description || code });
  }
  return out;
}
