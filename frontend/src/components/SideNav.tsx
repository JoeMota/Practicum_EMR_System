import type { ReactNode } from "react";
import { useState } from "react";
import { Box, Button, Drawer, Menu, MenuItem, Switch, Tooltip } from "@mui/material";
import DashboardOutlined from "@mui/icons-material/DashboardOutlined";
import FactCheckOutlined from "@mui/icons-material/FactCheckOutlined";
import PeopleAltOutlined from "@mui/icons-material/PeopleAltOutlined";
import BadgeOutlined from "@mui/icons-material/BadgeOutlined";
import HistoryOutlined from "@mui/icons-material/HistoryOutlined";
import SchoolOutlined from "@mui/icons-material/SchoolOutlined";
import QueryStatsOutlined from "@mui/icons-material/QueryStatsOutlined";
import AssessmentOutlined from "@mui/icons-material/AssessmentOutlined";
import MenuBookOutlined from "@mui/icons-material/MenuBookOutlined";
import MeetingRoomOutlined from "@mui/icons-material/MeetingRoomOutlined";
import GroupsOutlined from "@mui/icons-material/GroupsOutlined";
import LogoutOutlined from "@mui/icons-material/LogoutOutlined";
import TextFieldsOutlined from "@mui/icons-material/TextFieldsOutlined";
import { Link, NavLink, useLocation, useNavigate } from "react-router-dom";
import { useSession } from "../features/auth/useSession";
import { listReviewQueue } from "../api/notes";
import { useDisplayPrefs } from "../theme/useDisplayPrefs";
import { useAsync } from "../utils/useAsync";
import { utep } from "../theme/tokens";
import type { Role } from "../types";
import BrandLogo from "./BrandLogo";

export const SIDENAV_WIDTH = 232;

type NavItem = { to: string; label: string; icon: ReactNode; badge?: number; tabId?: string };

const ICON = {
  dashboard: <DashboardOutlined fontSize="small" />,
  review: <FactCheckOutlined fontSize="small" />,
  patients: <PeopleAltOutlined fontSize="small" />,
  roster: <BadgeOutlined fontSize="small" />,
  audit: <HistoryOutlined fontSize="small" />,
  courses: <SchoolOutlined fontSize="small" />,
  reports: <QueryStatsOutlined fontSize="small" />,
  cases: <MenuBookOutlined fontSize="small" />,
  lab: <MeetingRoomOutlined fontSize="small" />,
  teaching: <AssessmentOutlined fontSize="small" />,
};

function useNav(): NavItem[] {
  const { user, activeRole, courseId } = useSession();
  const queue = useAsync(
    () => (activeRole === "instructor" || activeRole === "course_coordinator") ? listReviewQueue(courseId, activeRole) : Promise.resolve([]),
    [user.id, activeRole, courseId],
  );
  const pending = queue.data?.filter((q) => q.note.status === "pending_review").length ?? 0;

  const byRole: Record<Role, NavItem[]> = {
    student: [
      { to: "/dashboard", label: "Dashboard", icon: ICON.dashboard },
      { to: "/patients", label: "My Patients", icon: ICON.patients },
      { to: "/my-activity", label: "My activity", icon: ICON.audit },
    ],
    instructor: [
      { to: "/dashboard", label: "Dashboard", icon: ICON.dashboard },
      { to: "/review", label: "Review queue", icon: ICON.review, badge: pending },
      { to: "/patients", label: "Patients", icon: ICON.patients },
      { to: "/cases", label: "Cases", icon: ICON.cases },
      { to: "/lab-checkin", label: "Lab check-in", icon: ICON.lab },
      { to: "/teaching", label: "Grades and time", icon: ICON.teaching },
      { to: "/audit", label: "Activity log", icon: ICON.audit },
    ],
    course_coordinator: [
      { to: "/dashboard", label: "Dashboard", icon: ICON.dashboard },
      { to: "/review", label: "Review queue", icon: ICON.review, badge: pending },
      { to: "/patients", label: "Patients", icon: ICON.patients },
      { to: "/cases", label: "Cases", icon: ICON.cases },
      { to: "/lab-checkin", label: "Lab check-in", icon: ICON.lab },
      { to: "/admin/roster", label: "Instructors", icon: ICON.roster },
      { to: "/teaching", label: "Grades and time", icon: ICON.teaching },
      { to: "/audit", label: "Activity log", icon: ICON.audit },
    ],
    admin: [
      { to: "/admin", label: "Home", icon: ICON.dashboard },
      { to: "/admin/courses", label: "Classes", icon: ICON.courses },
      { to: "/admin/people", label: "People", icon: ICON.roster },
      { to: "/admin/reports", label: "Reports", icon: ICON.reports },
      { to: "/admin/activity", label: "Activity log", icon: ICON.audit },
    ],
    front_desk: [{ to: "/patients", label: "Patients", icon: ICON.patients }],
    patient: [
      { to: "/portal?tab=overview", label: "Overview", icon: ICON.dashboard, tabId: "overview" },
      { to: "/portal?tab=health-record", label: "Health record", icon: ICON.patients, tabId: "health-record" },
      { to: "/portal?tab=my-information", label: "My information", icon: ICON.roster, tabId: "my-information" },
    ],
  };
  return byRole[activeRole];
}

const itemSx = {
  width: "100%", justifyContent: "flex-start", gap: 0.75, px: 1.5, py: 1, borderRadius: 1,
  color: "rgba(255,255,255,0.82)", fontSize: 14.5, fontWeight: 600,
  "&:hover": { bgcolor: "rgba(255,255,255,0.08)", color: "#fff" },
  "&.active": {
    bgcolor: "rgba(238,139,60,0.16)",
    color: "#fff",
    fontWeight: 700,
    boxShadow: `inset 3px 0 0 ${utep.orange}`,
  },
  "&.active:hover": { bgcolor: "rgba(238,139,60,0.22)" },
  "&.active .nav-badge": { bgcolor: utep.orange, color: utep.navy },
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

function NavContent({ onNavigate, collapsed }: { onNavigate?: () => void; collapsed?: boolean }) {
  const navigate = useNavigate();
  const location = useLocation();
  const { signOut } = useSession();
  const items = useNav();
  const portalTab = new URLSearchParams(location.search).get("tab") ?? "overview";

  return (
    <Box sx={{ height: "100%", display: "flex", flexDirection: "column", px: 1.5, py: 2.5, bgcolor: utep.navyDark }}>
      <Box sx={{ display: "flex", alignItems: "center", justifyContent: collapsed ? "center" : "flex-start", px: collapsed ? 0 : 1, pb: 2.5 }}>
        <BrandLogo variant={collapsed ? "mark" : "lockup"} compact={collapsed} />
      </Box>

      <Box component="nav" aria-label="Main" sx={{ display: "flex", flexDirection: "column", gap: 0.75 }}>
        {items.map((item) => {
          const selectedPortalTab = Boolean(
            item.tabId && location.pathname === "/portal" && portalTab === item.tabId,
          );
          const label = (
            <>
              {!collapsed && <Box component="span" sx={{ flex: 1, textAlign: "left" }}>{item.label}</Box>}
              {item.badge ? (
                <Box
                  component="span"
                  className="nav-badge"
                  aria-label={`${item.badge} awaiting review`}
                  sx={{
                    minWidth: 22, height: 22, px: 0.5, borderRadius: 1,
                    bgcolor: "rgba(238,139,60,0.9)", color: utep.navy, fontSize: 12, fontWeight: 800,
                    display: "grid", placeItems: "center",
                  }}
                >
                  {item.badge}
                </Box>
              ) : null}
            </>
          );
          const props = {
            key: item.to,
            startIcon: item.icon,
            onClick: onNavigate,
            "aria-label": item.label,
            title: collapsed ? item.label : undefined,
            sx: { ...itemSx, px: collapsed ? 1 : 1.75, justifyContent: collapsed ? "center" : "flex-start" },
          };
          return item.tabId ? (
            <Button
              {...props}
              component={Link}
              to={item.to}
              className={selectedPortalTab ? "active" : ""}
              aria-current={selectedPortalTab ? "page" : undefined}
            >
              {label}
            </Button>
          ) : (
            <Button
              {...props}
              component={NavLink}
              to={item.to}
              end={item.to === "/dashboard" || item.to === "/admin"}
            >
              {label}
            </Button>
          );
        })}
      </Box>

      <Box sx={{ flexGrow: 1, minHeight: 24 }} />

      <Tooltip title={collapsed ? "About us" : ""} placement="right">
        <Button
          component={NavLink}
          to="/about"
          startIcon={<GroupsOutlined fontSize="small" />}
          onClick={onNavigate}
          aria-label="About us"
          sx={{ ...itemSx, px: collapsed ? 1 : 1.75, justifyContent: collapsed ? "center" : "flex-start" }}
        >
          {!collapsed && "About us"}
        </Button>
      </Tooltip>
      {!collapsed && <DisplayPrefsButton />}
      <Tooltip title={collapsed ? "Sign out" : ""} placement="right">
        <Button startIcon={<LogoutOutlined fontSize="small" />} aria-label="Sign out" sx={{ ...itemSx, justifyContent: collapsed ? "center" : "flex-start" }} onClick={() => { signOut(); navigate("/"); }}>
          {!collapsed && "Sign out"}
        </Button>
      </Tooltip>
    </Box>
  );
}

interface Props {
  mobileOpen: boolean;
  onClose: () => void;
}

export default function SideNav({ mobileOpen, onClose }: Props) {
  const { prefs } = useDisplayPrefs();
  const width = prefs.navCollapsed ? 72 : SIDENAV_WIDTH;
  const paperSx = { width, boxSizing: "border-box", border: "none", bgcolor: utep.navy };
  return (
    <>
      <Drawer
        variant="temporary" open={mobileOpen} onClose={onClose} ModalProps={{ keepMounted: true }}
        sx={{ display: { xs: "block", md: "none" }, "& .MuiDrawer-paper": { ...paperSx, width: SIDENAV_WIDTH } }}
      >
        <NavContent onNavigate={onClose} />
      </Drawer>
      <Drawer
        variant="permanent" open
        sx={{ display: { xs: "none", md: "block" }, width, flexShrink: 0, "& .MuiDrawer-paper": paperSx }}
      >
        <NavContent collapsed={prefs.navCollapsed} />
      </Drawer>
    </>
  );
}
