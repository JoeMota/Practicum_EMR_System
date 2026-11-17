export const utep = {
  navy: "#0E2250",
  navyDark: "#081636",
  navyMid: "#163066",
  orange: "#EE8B3C",
  orangeSoft: "#FDF1E6",
  ink: "#172033",
  ink2: "#46536A",
  line: "#D6DCE4",
  lineSoft: "#E8ECF1",
  page: "#EEF1F6",
  paper: "#FFFFFF",
  alert: "#B42318",
  alertSoft: "#FEF3F2",
} as const;

/** Body / UI text — Source Sans 3 (clinical, not Inter/Roboto). */
export const fontFamily = [
  '"Source Sans 3"',
  '"Source Sans Pro"',
  "Helvetica Neue",
  "Helvetica",
  "sans-serif",
].join(",");

/** Brand and page titles — Bricolage Grotesque. */
export const fontDisplay = [
  '"Bricolage Grotesque"',
  '"Source Sans 3"',
  "Helvetica Neue",
  "sans-serif",
].join(",");

/** Subtle navy atmosphere for app pages (not flat gray, not purple glow). */
export const pageAtmosphere = `
  radial-gradient(1200px 600px at 0% -10%, rgba(14, 34, 80, 0.07), transparent 55%),
  radial-gradient(900px 500px at 100% 0%, rgba(238, 139, 60, 0.06), transparent 50%),
  linear-gradient(180deg, #F5F7FA 0%, ${utep.page} 40%, #E9EDF3 100%)
`;

/** Login / entry full-bleed plane. */
export const brandAtmosphere = `
  radial-gradient(ellipse 80% 60% at 20% 30%, rgba(238, 139, 60, 0.22), transparent 55%),
  radial-gradient(ellipse 70% 50% at 85% 70%, rgba(22, 48, 102, 0.55), transparent 50%),
  linear-gradient(145deg, ${utep.navyDark} 0%, ${utep.navy} 42%, ${utep.navyMid} 100%)
`;

/** Thin accent rule — replaces the diagonal candy stripe as primary branding. */
export const brandAccentBar = `linear-gradient(90deg, ${utep.orange} 0%, ${utep.orange} 28%, transparent 28%)`;
