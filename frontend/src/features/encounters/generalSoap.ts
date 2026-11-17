import type { IcdCode, Patient } from "../../types";

export type HpiMnemonic = "oldcarts" | "scholar_mac";
export type RosStatus = "positive" | "negative" | "not_asked";
export type RosMode = "full" | "focused";

export interface NamedField {
  id: string;
  label: string;
}

export const OLDCARTS: NamedField[] = [
  { id: "onset", label: "Onset" },
  { id: "location", label: "Location" },
  { id: "duration", label: "Duration" },
  { id: "character", label: "Character" },
  { id: "aggravating", label: "Aggravating factors" },
  { id: "relieving", label: "Relieving factors" },
  { id: "radiation", label: "Radiation" },
  { id: "timing", label: "Timing" },
  { id: "severity", label: "Severity" },
];

export const SCHOLAR_MAC: NamedField[] = [
  { id: "symptoms", label: "Symptoms" },
  { id: "characteristics", label: "Characteristics" },
  { id: "history", label: "History" },
  { id: "onset", label: "Onset" },
  { id: "location", label: "Location" },
  { id: "aggravating", label: "Aggravating factors" },
  { id: "remitting", label: "Remitting factors" },
  { id: "medications", label: "Medications" },
  { id: "allergies", label: "Allergies" },
  { id: "conditions", label: "Conditions" },
];

export interface RosItem {
  id: string;
  label: string;
  focused: boolean;
}

export interface RosSystem {
  id: string;
  label: string;
  items: RosItem[];
}

export const ROS_SYSTEMS: RosSystem[] = [
  system("constitutional", "Constitutional", [
    ["fever", "Fever", true],
    ["chills", "Chills", false],
    ["fatigue", "Fatigue", true],
    ["weight_loss", "Weight loss", false],
  ]),
  system("heent", "HEENT", [
    ["headache", "Headache", true],
    ["vision", "Vision change", false],
    ["sore_throat", "Sore throat", false],
  ]),
  system("cardiovascular", "Cardiovascular", [
    ["chest_pain", "Chest pain", true],
    ["palpitations", "Palpitations", false],
    ["edema", "Edema", false],
  ]),
  system("respiratory", "Respiratory", [
    ["cough", "Cough", true],
    ["dyspnea", "Shortness of breath", true],
    ["wheeze", "Wheezing", false],
  ]),
  system("gastrointestinal", "Gastrointestinal", [
    ["nausea", "Nausea", true],
    ["abdominal_pain", "Abdominal pain", true],
    ["diarrhea", "Diarrhea", false],
  ]),
  system("genitourinary", "Genitourinary", [
    ["dysuria", "Dysuria", true],
    ["frequency", "Urinary frequency", false],
    ["hematuria", "Hematuria", false],
  ]),
  system("musculoskeletal", "Musculoskeletal", [
    ["joint_pain", "Joint pain", true],
    ["back_pain", "Back pain", false],
  ]),
  system("neurologic", "Neurologic", [
    ["dizziness", "Dizziness", false],
    ["weakness", "Weakness", true],
    ["numbness", "Numbness", false],
  ]),
  system("skin", "Skin", [
    ["rash", "Rash", true],
    ["itching", "Itching", false],
  ]),
  system("psychiatric", "Psychiatric", [
    ["anxiety", "Anxiety", false],
    ["mood", "Depressed mood", true],
  ]),
];

export interface ProblemPlan {
  medications: string;
  education: string;
  followUp: string;
  referrals: string;
}

export const EMPTY_PLAN: ProblemPlan = { medications: "", education: "", followUp: "", referrals: "" };

const PLAN_LABELS: { key: keyof ProblemPlan; label: string }[] = [
  { key: "medications", label: "Medications" },
  { key: "education", label: "Education" },
  { key: "followUp", label: "Follow-up" },
  { key: "referrals", label: "Referrals" },
];

function system(id: string, label: string, items: [string, string, boolean][]): RosSystem {
  return {
    id,
    label,
    items: items.map(([itemId, itemLabel, focused]) => ({ id: `${id}.${itemId}`, label: itemLabel, focused })),
  };
}

export function readJson<T>(raw: string | undefined, fallback: T): T {
  if (!raw?.trim()) return fallback;
  try {
    return JSON.parse(raw) as T;
  } catch {
    return fallback;
  }
}

export function hpiMnemonic(content: Record<string, string>): HpiMnemonic {
  return content.hpi_mnemonic === "scholar_mac" ? "scholar_mac" : "oldcarts";
}

export function hpiValues(content: Record<string, string>, mnemonic: HpiMnemonic): Record<string, string> {
  const key = mnemonic === "scholar_mac" ? "hpi_scholar" : "hpi_oldcarts";
  return readJson<Record<string, string>>(content[key], {});
}

export function rosMode(content: Record<string, string>): RosMode {
  return content.ros_mode === "focused" ? "focused" : "full";
}

export function rosChecks(content: Record<string, string>): Record<string, RosStatus> {
  const stored = readJson<Record<string, RosStatus>>(content.ros_checks, {});
  const checks: Record<string, RosStatus> = {};
  for (const group of ROS_SYSTEMS) {
    for (const item of group.items) checks[item.id] = stored[item.id] ?? "not_asked";
  }
  return checks;
}

export function visibleRos(mode: RosMode): RosSystem[] {
  if (mode === "full") return ROS_SYSTEMS;
  return ROS_SYSTEMS.map((group) => ({ ...group, items: group.items.filter((item) => item.focused) })).filter((group) => group.items.length > 0);
}

export function focusRos(checks: Record<string, RosStatus>): Record<string, RosStatus> {
  const next = { ...checks };
  for (const group of ROS_SYSTEMS) {
    for (const item of group.items) {
      if (!item.focused) next[item.id] = "not_asked";
    }
  }
  return next;
}

export function legacyProse(raw: string | undefined): string {
  const text = raw?.trim() ?? "";
  if (!text || text.startsWith("{") || text.startsWith("[")) return "";
  return raw ?? "";
}

export function problemPlans(content: Record<string, string>): Record<string, ProblemPlan> {
  return readJson<Record<string, ProblemPlan>>(content.problem_plans, {});
}

export function planFor(plans: Record<string, ProblemPlan>, code: string): ProblemPlan {
  return { ...EMPTY_PLAN, ...(plans[code] ?? {}) };
}

export function compileNarrative(patient: Patient, content: Record<string, string>, diagnoses: IcdCode[]): string {
  const mnemonic = hpiMnemonic(content);
  const fields = mnemonic === "scholar_mac" ? SCHOLAR_MAC : OLDCARTS;
  const values = hpiValues(content, mnemonic);
  const hpiLines = fields.filter((field) => values[field.id]?.trim()).map((field) => `${field.label}: ${values[field.id].trim()}`);
  if (content.hpi?.trim()) hpiLines.push(content.hpi.trim());

  const checks = rosChecks(content);
  const rosLines: string[] = [];
  for (const group of ROS_SYSTEMS) {
    const marked = group.items.filter((item) => checks[item.id] === "positive" || checks[item.id] === "negative");
    if (!marked.length) continue;
    rosLines.push(`${group.label}: ${marked.map((item) => `${item.label} (${checks[item.id] === "positive" ? "positive" : "negative"})`).join(", ")}`);
  }
  const olderRos = legacyProse(content.ros);
  if (olderRos) rosLines.push(olderRos);

  const vitals = patient.vitals.filter((item) => item.status !== "entered_in_error").map((item) => `${item.label}: ${item.value}`);
  const objective = [content.exam?.trim(), vitals.length ? `Vitals: ${vitals.join("; ")}` : ""].filter(Boolean);

  const assessment = diagnoses.map((item, index) => {
    const why = item.rationale?.trim() ? `\nRationale: ${item.rationale.trim()}` : "";
    return `${index + 1}. ${item.code} ${item.label}${why}`;
  });
  if (content.rationale?.trim()) assessment.push(content.rationale.trim());

  const plans = problemPlans(content);
  const planBlocks = diagnoses.map((item, index) => {
    const plan = planFor(plans, item.code);
    const lines = PLAN_LABELS.filter((field) => plan[field.key]?.trim()).map((field) => `${field.label}: ${plan[field.key].trim()}`);
    return [`${index + 1}. ${item.label}`, ...(lines.length ? lines : ["Not documented"])].join("\n");
  });
  const olderPlan = legacyProse(content.plan);
  if (olderPlan) planBlocks.push(olderPlan);
  if (content.disposition?.trim()) planBlocks.push(`Disposition: ${content.disposition.trim()}`);

  return [
    section("Subjective", [
      line("Chief complaint", content.cc?.trim() || patient.chiefComplaint),
      block(mnemonic === "scholar_mac" ? "History of present illness (SCHOLAR-MAC)" : "History of present illness (OLDCARTS)", hpiLines),
      block("Review of systems", rosLines),
      line("History", content.history?.trim()),
    ]),
    section("Objective", objective),
    section("Assessment", assessment),
    section("Plan", planBlocks),
  ].join("\n\n");
}

function line(label: string, value: string | undefined): string {
  return value?.trim() ? `${label}: ${value.trim()}` : "";
}

function block(label: string, lines: string[]): string {
  if (!lines.length) return "";
  return `${label}:\n${lines.join("\n")}`;
}

function section(title: string, parts: string[]): string {
  const body = parts.map((part) => part.trim()).filter(Boolean).join("\n");
  return `${title.toUpperCase()}\n${body || "Not documented"}`;
}
