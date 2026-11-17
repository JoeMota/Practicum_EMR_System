export type MedRecAction = "Continue" | "Modify" | "Discontinue" | "Hold";
export type MedRecValue = Record<string, { action?: MedRecAction; comment?: string }>;

export function parseMedRec(raw?: string): MedRecValue {
  try {
    return raw ? JSON.parse(raw) : {};
  } catch {
    return {};
  }
}
