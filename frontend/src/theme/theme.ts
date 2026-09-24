import { createTheme } from "@mui/material/styles";
import { fontFamily, utep } from "./tokens";

export interface DisplayPrefs {
  textScale: 1 | 1.15 | 1.3;
  highContrast: boolean;
}

export function createAppTheme({ textScale, highContrast }: DisplayPrefs) {
  const line = highContrast ? "#5B6577" : utep.line;
  const ink2 = highContrast ? utep.ink : utep.ink2;

  return createTheme({
    palette: {
      primary: { main: utep.navy, dark: utep.navyDark, contrastText: "#FFFFFF" },
      secondary: { main: utep.orange, contrastText: utep.navy },
      error: { main: utep.alert },
      warning: { main: "#B54708" },
      success: { main: "#067647" },
      info: { main: "#175CD3" },
      background: { default: highContrast ? "#FFFFFF" : utep.page, paper: utep.paper },
      text: { primary: utep.ink, secondary: ink2 },
      divider: line,
    },
    shape: { borderRadius: 6 },
    typography: {
      fontFamily,
      fontSize: 14 * textScale,
      h4: { fontWeight: 700, letterSpacing: "-0.02em" },
      h5: { fontWeight: 700, letterSpacing: "-0.015em" },
      h6: { fontWeight: 700, letterSpacing: "-0.01em" },
      subtitle1: { fontWeight: 600 },
      subtitle2: { fontWeight: 700 },
      button: { textTransform: "none", fontWeight: 600 },
      overline: { textTransform: "none", letterSpacing: 0, fontWeight: 600 },
    },
    components: {
      MuiCssBaseline: {
        styleOverrides: {
          body: { fontVariantNumeric: "tabular-nums" },
          "*:focus-visible": { outline: `3px solid ${utep.navy}`, outlineOffset: 2 },
          "@keyframes emrFadeIn": {
            from: { opacity: 0, transform: "translateY(6px)" },
            to: { opacity: 1, transform: "translateY(0)" },
          },
          "@media (prefers-reduced-motion: reduce)": {
            "*": { animationDuration: "0.01ms !important", transitionDuration: "0.01ms !important" },
          },
        },
      },
      MuiButton: {
        defaultProps: { disableElevation: true },
        styleOverrides: {
          root: {
            transition: "background-color 140ms ease, color 140ms ease, border-color 140ms ease, transform 140ms ease",
            "&:active:not(:disabled)": { transform: "translateY(1px)" },
          },
        },
      },
      MuiPaper: {
        defaultProps: { elevation: 0 },
        styleOverrides: {
          root: {
            border: `1px solid ${line}`,
            transition: "border-color 160ms ease, box-shadow 160ms ease",
          },
        },
      },
      MuiTableRow: {
        styleOverrides: {
          root: {
            transition: "background-color 120ms ease",
          },
        },
      },
      MuiAppBar: { styleOverrides: { root: { border: "none" } } },
      MuiMenu: { styleOverrides: { paper: { boxShadow: "0 8px 24px rgba(14,34,80,0.14)" } } },
      MuiTableCell: {
        styleOverrides: {
          head: { fontWeight: 700, color: ink2, backgroundColor: highContrast ? "#FFFFFF" : "#F7F8FA" },
          root: { borderColor: line },
        },
      },
      MuiTab: { styleOverrides: { root: { textTransform: "none", fontWeight: 600, minHeight: 48 } } },
      MuiChip: { styleOverrides: { root: { fontWeight: 600 } } },
      MuiTooltip: { defaultProps: { arrow: true } },
      MuiLinearProgress: {
        styleOverrides: {
          root: { borderRadius: 999, height: 4 },
        },
      },
    },
  });
}
