import { useMemo, useState, type ReactNode } from "react";
import { CssBaseline, ThemeProvider } from "@mui/material";
import { createAppTheme, type DisplayPrefs } from "./theme";
import { DisplayPrefsContext } from "./useDisplayPrefs";

const KEY = "emr.displayPrefs";
const defaults: DisplayPrefs = { textScale: 1, highContrast: false, navCollapsed: false };

function load(): DisplayPrefs {
  try {
    return { ...defaults, ...JSON.parse(localStorage.getItem(KEY) ?? "{}") };
  } catch {
    return defaults;
  }
}

export function DisplayPrefsProvider({ children }: { children: ReactNode }) {
  const [prefs, setState] = useState<DisplayPrefs>(load);
  const theme = useMemo(() => createAppTheme(prefs), [prefs]);

  const setPrefs = (p: Partial<DisplayPrefs>) =>
    setState((prev) => {
      const next = { ...prev, ...p };
      try {
        localStorage.setItem(KEY, JSON.stringify(next));
      } catch {
        /* storage unavailable: prefs last for this session */
      }
      return next;
    });

  return (
    <DisplayPrefsContext.Provider value={{ prefs, setPrefs }}>
      <ThemeProvider theme={theme}>
        <CssBaseline />
        {children}
      </ThemeProvider>
    </DisplayPrefsContext.Provider>
  );
}
