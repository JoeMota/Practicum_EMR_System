import type { Discipline } from "../../types";

const PACKS: Record<Discipline, string[]> = {
  pharmacy: [
    "Medication experience: takes doses as scheduled, no missed doses this week.",
    "Monitoring: recheck the relevant lab before the next visit.",
  ],
  nursing: [
    "Safety: call light in reach and bed in low position.",
    "Education: reviewed warning signs and when to call.",
  ],
  physical_therapy: [
    "Tolerated the session with no increase in pain.",
    "Home program reviewed and the patient demonstrated it back.",
  ],
  occupational_therapy: [
    "Practiced the daily task with standby assist.",
    "Adaptive strategy reviewed for the next session.",
  ],
  speech_language_pathology: [
    "Swallow trial completed without overt signs of aspiration.",
    "Communication strategy practiced with the patient.",
  ],
};

export function suggestionsFor(discipline?: Discipline): string[] {
  if (!discipline) return PACKS.pharmacy;
  return PACKS[discipline] ?? PACKS.pharmacy;
}
