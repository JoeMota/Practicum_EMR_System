import { useState } from "react";
import { Box } from "@mui/material";
import { Outlet } from "react-router-dom";
import { utep } from "../theme/tokens";
import AppHeader from "./AppHeader";
import SideNav from "./SideNav";
import { PageHeadingProvider } from "./PageHeading";
import LabAssignmentStrip from "../features/simLab/LabAssignmentStrip";

export default function AppShell() {
  const [navOpen, setNavOpen] = useState(false);

  return (
    <PageHeadingProvider>
      <Box sx={{ display: "flex", minHeight: "100vh", bgcolor: "background.default" }}>
        <Box
          component="a" href="#main"
          sx={{
            position: "absolute", left: 8, top: -48, zIndex: 2000, px: 2, py: 1, borderRadius: 1,
            bgcolor: utep.navy, color: "#fff", fontWeight: 700, "&:focus": { top: 8 },
          }}
        >
          Skip to content
        </Box>

        <SideNav mobileOpen={navOpen} onClose={() => setNavOpen(false)} />

        <Box sx={{ flex: 1, minWidth: 0, display: "flex", flexDirection: "column" }}>
          <AppHeader onOpenNav={() => setNavOpen(true)} />
          <Box component="main" id="main" tabIndex={-1} sx={{ flex: 1, p: { xs: 2, md: 3 }, outline: "none" }}>
            <LabAssignmentStrip />
            <Outlet />
          </Box>
        </Box>
      </Box>
    </PageHeadingProvider>
  );
}
