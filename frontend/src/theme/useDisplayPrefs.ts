import { createContext, useContext } from "react";
import type { DisplayPrefs } from "./theme";

export interface DisplayPrefsCtx {
  prefs: DisplayPrefs;
  setPrefs: (p: Partial<DisplayPrefs>) => void;
}

export const DisplayPrefsContext = createContext<DisplayPrefsCtx | null>(null);

export function useDisplayPrefs() {
  const ctx = useContext(DisplayPrefsContext);
  if (!ctx) throw new Error("useDisplayPrefs must be used inside DisplayPrefsProvider");
  return ctx;
}
