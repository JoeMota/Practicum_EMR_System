import { createTheme } from "@mui/material/styles";
import { fontDisplay, fontFamily, pageAtmosphere, utep } from "./tokens";

export interface DisplayPrefs {
  textScale: 1 | 1.15 | 1.3;
  highContrast: boolean;
  navCollapsed: boolean;
}

export function createAppTheme({ textScale, highContrast }: DisplayPrefs) {
  const line = highContrast ? "#5B6577" : utep.lineSoft;
  const ink2 = highContrast ? utep.ink : utep.ink2;
  const pageBg = highContrast ? "#FFFFFF" : utep.page;

  return createTheme({
    palette: {
      primary: { main: utep.navy, dark: utep.navyDark, contrastText: "#FFFFFF" },
      secondary: { main: utep.orange, contrastText: utep.navy },
      error: { main: utep.alert },
      warning: { main: "#B54708" },
      success: { main: "#067647" },
      info: { main: "#175CD3" },
      background: { default: pageBg, paper: utep.paper },
      text: { primary: utep.ink, secondary: ink2 },
      divider: line,
    },
    shape: { borderRadius: 4 },
    typography: {
      fontFamily,
      fontSize: 14 * textScale,
      h1: { fontFamily: fontDisplay, fontWeight: 700, letterSpacing: "-0.03em" },
      h2: { fontFamily: fontDisplay, fontWeight: 700, letterSpacing: "-0.025em" },
      h3: { fontFamily: fontDisplay, fontWeight: 700, letterSpacing: "-0.02em" },
      h4: { fontFamily: fontDisplay, fontWeight: 700, letterSpacing: "-0.02em" },
      h5: { fontFamily: fontDisplay, fontWeight: 700, letterSpacing: "-0.015em" },
      h6: { fontFamily: fontDisplay, fontWeight: 650, letterSpacing: "-0.01em" },
      subtitle1: { fontWeight: 600 },
      subtitle2: { fontWeight: 650 },
      button: { textTransform: "none", fontWeight: 600, fontFamily },
      overline: { textTransform: "none", letterSpacing: "0.04em", fontWeight: 600, fontSize: 11 * textScale },
    },
    components: {
      MuiCssBaseline: {
        styleOverrides: {
          body: {
            fontVariantNumeric: "tabular-nums",
            backgroundColor: pageBg,
            backgroundImage: highContrast ? "none" : pageAtmosphere,
            backgroundAttachment: "fixed",
          },
          "*:focus-visible": { outline: `3px solid ${utep.navy}`, outlineOffset: 2 },
          "@media (prefers-reduced-motion: reduce)": {
            "*": { animationDuration: "0.01ms !important", transitionDuration: "0.01ms !important" },
          },
        },
      },
      MuiButton: {
        defaultProps: { disableElevation: true },
        styleOverrides: {
          root: { borderRadius: 4 },
          contained: {
            "&.MuiButton-colorPrimary:hover": { backgroundColor: utep.navyMid },
          },
        },
      },
      MuiPaper: {
        defaultProps: { elevation: 0 },
        // Border only when a component opts in via variant="outlined" — not every Paper.
        styleOverrides: {
          root: { backgroundImage: "none" },
          outlined: { border: `1px solid ${line}` },
        },
      },
      MuiAppBar: { styleOverrides: { root: { border: "none", boxShadow: "none" } } },
      MuiDrawer: {
        styleOverrides: {
          paper: {
            border: "none",
            borderRight: `1px solid ${line}`,
            backgroundImage: "none",
          },
        },
      },
      MuiMenu: {
        styleOverrides: {
          paper: {
            border: `1px solid ${line}`,
            boxShadow: "0 10px 28px rgba(14,34,80,0.10)",
          },
        },
      },
      MuiTableCell: {
        styleOverrides: {
          head: {
            fontWeight: 700,
            color: utep.ink,
            backgroundColor: highContrast ? "#F0F2F5" : "rgba(14, 34, 80, 0.04)",
            borderBottom: `2px solid ${utep.navy}`,
            fontSize: 12.5 * textScale,
          },
          root: { borderColor: line },
        },
      },
      MuiTab: {
        styleOverrides: {
          root: {
            textTransform: "none",
            fontWeight: 600,
            minHeight: 44,
            fontFamily,
          },
        },
      },
      MuiTabs: {
        styleOverrides: {
          indicator: { height: 3, backgroundColor: utep.orange },
        },
      },
      MuiChip: {
        styleOverrides: {
          root: { fontWeight: 600, borderRadius: 4 },
        },
      },
      MuiTooltip: { defaultProps: { arrow: true } },
      MuiTextField: {
        defaultProps: { variant: "outlined", size: "small" },
      },
      MuiOutlinedInput: {
        styleOverrides: {
          root: { backgroundColor: utep.paper },
        },
      },
    },
  });
}
