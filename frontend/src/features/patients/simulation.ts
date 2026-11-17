import type { ClinicalNote, Patient, SimulationPhase } from "../../types";

export function phaseChip(phase?: SimulationPhase | null): { label: string; bgcolor: string; color: string } {
  if (phase === "ready") {
    return { label: "Ready for visit note / fill verify", bgcolor: "#E6F4EA", color: "#0D652D" };
  }
  if (phase === "closed") {
    return { label: "Note closed", bgcolor: "#F1F3F4", color: "#3C4043" };
  }
  return { label: "Waiting for vitals", bgcolor: "#FEF7E0", color: "#8A5A00" };
}

export function simulationNoteAction(
  patient: Patient, notes: ClinicalNote[], userId: string,
): { href: string; label: string } | null {
  if (patient.mode !== "simulation") return null;
  const phase = patient.simulationPhase ?? "waiting_vitals";
  if (phase === "waiting_vitals") return null;
  if (phase === "ready") {
    if (patient.viewerStation !== "pharmacist" && patient.viewerStation !== "provider") return null;
    const draft = notes.find((note) => (note.kind ?? "visit") === "visit" && (note.status === "draft" || note.status === "returned"));
    if (draft) return { href: `/patients/${patient.id}/notes/${draft.id}`, label: "Continue visit note" };
    if (notes.some((note) => (note.kind ?? "visit") === "visit")) {
      if (patient.viewerStation === "pharmacist") {
        return { href: `/patients/${patient.id}?tab=medications`, label: "Open fill verification" };
      }
      return null;
    }
    return { href: `/patients/${patient.id}/notes/new`, label: "Start visit note" };
  }
  const open = notes.find((note) => note.kind === "clarification" && note.authorId === userId && (note.status === "draft" || note.status === "returned"));
  if (open) return { href: `/patients/${patient.id}/notes/${open.id}`, label: "Continue clarification" };
  return { href: `/patients/${patient.id}/notes/new?kind=clarification`, label: "New clarification note" };
}
