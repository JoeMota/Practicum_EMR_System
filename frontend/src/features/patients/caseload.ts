import type { PatientRow } from "../../api/patients";
import type { EncounterStatus } from "../../types";

const IN_CLINIC = new Set<EncounterStatus>(["In progress", "Checked in", "Roomed"]);

export const CASELOAD_VIEWS = [
  {
    id: "assigned",
    label: "Assigned patients",
    description: "Cases your instructor assigned to you. Each one is your own copy: no one else's notes appear on it.",
    emptyTitle: "No assigned patients yet",
    emptyBody: "Your instructor will assign cases here.",
  },
  {
    id: "in-clinic",
    label: "In clinic now",
    description: "Patients who are checked in, roomed, or in a visit right now.",
    emptyTitle: "No one is in clinic right now",
    emptyBody: "Checked-in, roomed, and in-progress visits show up here.",
  },
  {
    id: "returned",
    label: "Returned notes",
    description: "Notes your instructor sent back for you to revise and resubmit.",
    emptyTitle: "No returned notes",
    emptyBody: "When an instructor returns a note, that patient shows up here.",
  },
  {
    id: "awaiting",
    label: "Needs review",
    description: "Notes you submitted that are waiting on your instructor.",
    emptyTitle: "No notes awaiting review",
    emptyBody: "Submitted notes waiting for an instructor appear here.",
  },
  {
    id: "flags",
    label: "Items to check",
    description: "Charts that still have a dose warning.",
    emptyTitle: "No dose warnings",
    emptyBody: "Unclear or extreme doses show up here until they are corrected or cleared.",
  },
  {
    id: "practice",
    label: "Practice cases",
    description: "Shared patients for learning the system. Nothing here is graded, and instructors reset them between sessions.",
    emptyTitle: "No practice cases",
    emptyBody: "Practice patients for this course will show up here.",
  },
] as const;

export type CaseloadView = (typeof CASELOAD_VIEWS)[number]["id"];

export function parseCaseloadView(value: string | null): CaseloadView | undefined {
  return CASELOAD_VIEWS.find((view) => view.id === value)?.id;
}

export function caseloadViewMeta(view: CaseloadView) {
  return CASELOAD_VIEWS.find((item) => item.id === view)!;
}

export function caseloadHref(view: CaseloadView, query = "") {
  const params = new URLSearchParams({ view });
  if (query) params.set("q", query);
  return `/patients?${params.toString()}`;
}

export function matchesCaseload(row: PatientRow, view: CaseloadView): boolean {
  if (row.patient.mode === "case") return false;
  switch (view) {
    case "assigned":
      return row.patient.mode === "assessment";
    case "practice":
      return row.patient.mode === "practice";
    case "in-clinic":
      return IN_CLINIC.has(row.patient.status.encounter);
    case "returned":
      return row.latestNote?.status === "returned";
    case "awaiting":
      return row.latestNote?.status === "pending_review";
    case "flags":
      return (row.openFlagCount ?? 0) > 0;
  }
}
