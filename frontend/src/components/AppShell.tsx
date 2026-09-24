import { Box, Link } from "@mui/material";
import { Outlet } from "react-router-dom";
import AppHeader from "./AppHeader";

export default function AppShell() {
  return (
    <Box sx={{ minHeight: "100dvh", bgcolor: "background.default" }}>
      <Link
        href="#main"
        sx={{
          position: "absolute", left: 8, top: -48, zIndex: 2000, bgcolor: "background.paper", p: 1, borderRadius: 1,
          "&:focus": { top: 8 },
        }}
      >
        Skip to content
      </Link>
      <AppHeader />
      <Box
        component="main"
        id="main"
        tabIndex={-1}
        sx={{
          px: { xs: 2, md: 4 },
          py: 3,
          maxWidth: 1440,
          mx: "auto",
          outline: "none",
          animation: "emrFadeIn 200ms ease-out",
        }}
      >
        <Outlet />
      </Box>
    </Box>
  );
}
