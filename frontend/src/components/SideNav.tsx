import type { ReactNode } from "react";
import { useState } from "react";
import { Box, Button, Drawer, Menu, MenuItem, Switch, Typography } from "@mui/material";
import DashboardOutlined from "@mui/icons-material/DashboardOutlined";
import FactCheckOutlined from "@mui/icons-material/FactCheckOutlined";
import PeopleAltOutlined from "@mui/icons-material/PeopleAltOutlined";
import BadgeOutlined from "@mui/icons-material/BadgeOutlined";
import HistoryOutlined from "@mui/icons-material/HistoryOutlined";
import SchoolOutlined from "@mui/icons-material/SchoolOutlined";
import QueryStatsOutlined from "@mui/icons-material/QueryStatsOutlined";
import LogoutOutlined from "@mui/icons-material/LogoutOutlined";
import TextFieldsOutlined from "@mui/icons-material/TextFieldsOutlined";
import { NavLink, useNavigate } from "react-router-dom";
import { useSession } from "../features/auth/AuthContext";
import { listReviewQueue } from "../api/notes";
import { useDisplayPrefs } from "../theme/DisplayPrefsProvider";
import { useAsync } from "../utils/useAsync";
import { utep } from "../theme/tokens";
import type { Role } from "../types";

export const SIDENAV_WIDTH = 248;

type NavItem = { to: string; label: string; icon: ReactNode; badge?: number };

const ICON = {
  dashboard: <DashboardOutlined fontSize="small" />,
  review: <FactCheckOutlined fontSize="small" />,
  patients: <PeopleAltOutlined fontSize="small" />,
  roster: <BadgeOutlined fontSize="small" />,
  audit: <HistoryOutlined fontSize="small" />,
  courses: <SchoolOutlined fontSize="small" />,
  reports: <QueryStatsOutlined fontSize="small" />,
};

function useNav(): NavItem[] {
  const { user, activeRole, courseId } = useSession();
  const queue = useAsync(
    () => activeRole === "instructor" ? listReviewQueue(courseId, activeRole) : Promise.resolve([]),
    [user.id, activeRole, courseId],
  );
  const pending = queue.data?.filter((q) => q.note.status === "pending_review").length ?? 0;

  const byRole: Record<Role, NavItem[]> = {
    student: [
      { to: "/dashboard", label: "Dashboard", icon: ICON.dashboard },
      { to: "/patients", label: "My Patients", icon: ICON.patients },
    ],
    instructor: [
      { to: "/dashboard", label: "Dashboard", icon: ICON.dashboard },
      { to: "/review", label: "Review queue", icon: ICON.review, badge: pending },
      { to: "/patients", label: "Patients", icon: ICON.patients },
      { to: "/admin/roster", label: "Roster", icon: ICON.roster },
      { to: "/audit", label: "Activity log", icon: ICON.audit },
    ],
    admin: [
      { to: "/admin/courses", label: "Courses", icon: ICON.courses },
      { to: "/admin/reports", label: "Reports", icon: ICON.reports },
      { to: "/admin/roster", label: "Roster", icon: ICON.roster },
      { to: "/audit", label: "Activity log", icon: ICON.audit },
      { to: "/patients", label: "Patients", icon: ICON.patients },
    ],
    front_desk: [{ to: "/patients", label: "Patients", icon: ICON.patients }],
    patient: [],
  };
  return byRole[activeRole];
}

const itemSx = {
  width: "100%", justifyContent: "flex-start", gap: 0.75, px: 1.75, py: 1.15, borderRadius: "10px",
  color: "rgba(255,255,255,0.85)", fontSize: 15, fontWeight: 600,
  "&:hover": { bgcolor: "rgba(255,255,255,0.08)", color: "#fff" },
  "&.active": { bgcolor: utep.orange, color: utep.navy, fontWeight: 700 },
  "&.active:hover": { bgcolor: utep.orange },
  "&.active .nav-badge": { bgcolor: utep.navy, color: "#fff" },
  "&:focus-visible": { outline: `3px solid ${utep.orange}`, outlineOffset: 2 },
} as const;

function DisplayPrefsButton() {
  const { prefs, setPrefs } = useDisplayPrefs();
  const [anchor, setAnchor] = useState<HTMLElement | null>(null);

  return (
    <>
      <Button startIcon={<TextFieldsOutlined fontSize="small" />} sx={itemSx} onClick={(e) => setAnchor(e.currentTarget)}>
        Text size & contrast
      </Button>
      <Menu
        anchorEl={anchor} open={Boolean(anchor)} onClose={() => setAnchor(null)}
        anchorOrigin={{ vertical: "top", horizontal: "right" }}
        transformOrigin={{ vertical: "bottom", horizontal: "left" }}
      >
        <MenuItem selected={prefs.textScale === 1} onClick={() => setPrefs({ textScale: 1 })}>Default text</MenuItem>
        <MenuItem selected={prefs.textScale === 1.15} onClick={() => setPrefs({ textScale: 1.15 })}>Larger text</MenuItem>
        <MenuItem selected={prefs.textScale === 1.3} onClick={() => setPrefs({ textScale: 1.3 })}>Largest text</MenuItem>
        <MenuItem onClick={() => setPrefs({ highContrast: !prefs.highContrast })}>
          <Box sx={{ display: "flex", alignItems: "center", gap: 1, width: "100%" }}>
            High contrast
            <Switch size="small" checked={prefs.highContrast} sx={{ ml: "auto" }} />
          </Box>
        </MenuItem>
      </Menu>
    </>
  );
}

function NavContent({ onNavigate }: { onNavigate?: () => void }) {
  const navigate = useNavigate();
  const { signOut } = useSession();
  const items = useNav();

  return (
    <Box sx={{ height: "100%", display: "flex", flexDirection: "column", px: 2, py: 3.5, bgcolor: utep.navy }}>
      <Box sx={{ display: "flex", alignItems: "center", gap: 1.25, px: 1.25, pb: 3.5 }}>
        <Box
          aria-hidden
          sx={{
            width: 38, height: 38, borderRadius: "9px", bgcolor: utep.orange, color: utep.navy,
            display: "grid", placeItems: "center", fontWeight: 800, fontSize: 15,
          }}
        >
          UT
        </Box>
        <Box>
          <Typography sx={{ color: "#fff", fontWeight: 800, fontSize: 18, lineHeight: 1.2 }}>UTEP EMR</Typography>
          <Typography variant="caption" sx={{ color: "rgba(255,255,255,0.75)" }}>Training system</Typography>
        </Box>
      </Box>

      <Box component="nav" aria-label="Main" sx={{ display: "flex", flexDirection: "column", gap: 0.75 }}>
        {items.map((item) => (
          <Button
            key={item.to}
            component={NavLink}
            to={item.to}
            end={item.to === "/dashboard"}
            startIcon={item.icon}
            onClick={onNavigate}
            sx={itemSx}
          >
            <Box component="span" sx={{ flex: 1, textAlign: "left" }}>{item.label}</Box>
            {item.badge ? (
              <Box
                component="span"
                className="nav-badge"
                aria-label={`${item.badge} awaiting review`}
                sx={{
                  minWidth: 22, height: 22, px: 0.5, borderRadius: "999px",
                  bgcolor: utep.orange, color: utep.navy, fontSize: 12, fontWeight: 800,
                  display: "grid", placeItems: "center",
                }}
              >
                {item.badge}
              </Box>
            ) : null}
          </Button>
        ))}
      </Box>

      <Box sx={{ flexGrow: 1, minHeight: 24 }} />

      <DisplayPrefsButton />
      <Button startIcon={<LogoutOutlined fontSize="small" />} sx={itemSx} onClick={() => { signOut(); navigate("/"); }}>
        Sign out
      </Button>
    </Box>
  );
}

interface Props {
  mobileOpen: boolean;
  onClose: () => void;
}

export default function SideNav({ mobileOpen, onClose }: Props) {
  const paperSx = { width: SIDENAV_WIDTH, boxSizing: "border-box", border: "none", bgcolor: utep.navy };
  return (
    <>
      <Drawer
        variant="temporary" open={mobileOpen} onClose={onClose} ModalProps={{ keepMounted: true }}
        sx={{ display: { xs: "block", md: "none" }, "& .MuiDrawer-paper": paperSx }}
      >
        <NavContent onNavigate={onClose} />
      </Drawer>
      <Drawer
        variant="permanent" open
        sx={{ display: { xs: "none", md: "block" }, width: SIDENAV_WIDTH, flexShrink: 0, "& .MuiDrawer-paper": paperSx }}
      >
        <NavContent />
      </Drawer>
    </>
  );
}
