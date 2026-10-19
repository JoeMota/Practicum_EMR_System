import { useState, type FormEvent } from "react";
import {
  AppBar, Box, Chip, Divider, FormControlLabel, IconButton, InputBase, Menu, MenuItem, Select,
  Switch, ToggleButton, ToggleButtonGroup, Toolbar, Tooltip, Typography,
} from "@mui/material";
import MenuRounded from "@mui/icons-material/MenuRounded";
import SearchRounded from "@mui/icons-material/SearchRounded";
import TextIncreaseOutlined from "@mui/icons-material/TextIncreaseOutlined";
import { useLocation, useNavigate } from "react-router-dom";
import { useSession } from "../features/auth/AuthContext";
import { getCourse, listCoursesForUser } from "../api/courses";
import { useDisplayPrefs } from "../theme/DisplayPrefsProvider";
import { trainingStripe, utep } from "../theme/tokens";
import { disciplineLabel, roleLabel } from "../utils/labels";
import { homePathFor } from "../utils/permissions";
import { useAsync } from "../utils/useAsync";
import { usePageHeadingValue } from "./PageHeading";
import type { Role } from "../types";

const pickerSx = {
  bgcolor: "#fff", color: utep.navy, fontWeight: 600, borderRadius: "10px", height: 44,
  "& fieldset": { border: "none" },
};

export default function AppHeader({ onOpenNav }: { onOpenNav: () => void }) {
  const navigate = useNavigate();
  const location = useLocation();
  const heading = usePageHeadingValue();
  const { user, activeRole, discipline, courseId, switchRole, selectCourse } = useSession();
  const { prefs, setPrefs } = useDisplayPrefs();
  const [q, setQ] = useState("");
  const [anchor, setAnchor] = useState<HTMLElement | null>(null);
  const { data: courses = [] } = useAsync(() => listCoursesForUser(), [user.id]);
  const course = useAsync(() => getCourse(courseId), [courseId]);

  const roleCourses = courses.filter((c) => user.roles.find((r) => r.role === activeRole)?.courseIds.includes(c.id));
  const initials = user.fullName.split(" ").map((w) => w[0]).slice(0, 2).join("");
  const canSearch = activeRole !== "patient";
  const courseLabel = course.data
    ? `${course.data.code}: ${course.data.title}${course.data.term ? `, ${course.data.term}` : ""}`
    : " ";

  const search = (e: FormEvent) => {
    e.preventDefault();
    const term = q.trim();
    const next = new URLSearchParams(location.pathname === "/patients" ? location.search : "");
    if (term) next.set("q", term);
    else next.delete("q");
    const qs = next.toString();
    navigate(qs ? `/patients?${qs}` : "/patients");
  };

  return (
    <>
      <AppBar
        position="sticky" elevation={0}
        sx={{ bgcolor: utep.orange, color: utep.navy, borderBottom: `4px solid ${utep.navy}` }}
      >
        <Toolbar sx={{ gap: 1.5, flexWrap: "wrap", py: 1.5, px: { xs: 2, md: 3 }, minHeight: { md: 76 } }}>
          <IconButton
            aria-label="Open navigation" onClick={onOpenNav}
            sx={{ display: { md: "none" }, color: utep.navy }}
          >
            <MenuRounded />
          </IconButton>

          <Box sx={{ flex: "1 1 220px", minWidth: 0 }}>
            <Typography component="h1" sx={{ fontWeight: 800, fontSize: heading ? 22 : 16, lineHeight: 1.2, color: utep.navy }}>
              {heading?.title ?? courseLabel}
            </Typography>
            {heading && (
              <Typography sx={{ fontSize: 13, fontWeight: 600, color: utep.navy, opacity: 0.85 }}>{courseLabel}</Typography>
            )}
          </Box>

          {canSearch && (
            <Box
              component="form" role="search" onSubmit={search}
              sx={{
                flex: "0 1 280px", display: "flex", alignItems: "center", gap: 1, px: 1.75, height: 44,
                bgcolor: "#fff", borderRadius: "999px", color: "text.secondary",
              }}
            >
              <SearchRounded fontSize="small" />
              <InputBase
                value={q} onChange={(e) => {
                  const value = e.target.value;
                  setQ(value);
                  if (location.pathname !== "/patients") return;
                  const next = new URLSearchParams(location.search);
                  const term = value.trim();
                  if (term) next.set("q", term);
                  else next.delete("q");
                  const qs = next.toString();
                  navigate(qs ? `/patients?${qs}` : "/patients", { replace: true });
                }}
                sx={{ flex: 1, fontSize: 14 }}
                placeholder={activeRole === "student" ? "Search name or MRN" : "Search patient, MRN, or student"}
                inputProps={{ "aria-label": "Search patients" }}
              />
            </Box>
          )}

          {roleCourses.length > 1 && (
            <Select
              size="small" value={courseId} inputProps={{ "aria-label": "Course" }}
              onChange={(e) => {
                selectCourse(e.target.value);
                // Leave chart/review deep links so we don't show another course's patient.
                navigate(homePathFor(activeRole));
              }}
              sx={{ ...pickerSx, minWidth: 140 }}
            >
              {roleCourses.map((c) => <MenuItem key={c.id} value={c.id}>{c.code}</MenuItem>)}
            </Select>
          )}

          {user.roles.length > 1 && (
            <Select
              size="small" value={activeRole} inputProps={{ "aria-label": "Acting as" }}
              onChange={(e) => {
                const role = e.target.value as Role;
                switchRole(role);
                navigate(homePathFor(role));
              }}
              sx={{ ...pickerSx, bgcolor: utep.navy, color: "#fff", borderRadius: "999px", "& .MuiSvgIcon-root": { color: "#fff" } }}
              renderValue={(v) => `Acting as: ${roleLabel[v as Role]}`}
            >
              {user.roles.map((r) => <MenuItem key={r.role} value={r.role}>{roleLabel[r.role]}</MenuItem>)}
            </Select>
          )}

          <Tooltip title="Text size and contrast">
            <IconButton aria-label="Display settings" sx={{ color: utep.navy }} onClick={(e) => setAnchor(e.currentTarget)}>
              <TextIncreaseOutlined />
            </IconButton>
          </Tooltip>
          <Menu anchorEl={anchor} open={Boolean(anchor)} onClose={() => setAnchor(null)}>
            <Box sx={{ px: 2, py: 1.5, width: 260 }}>
              <Typography variant="subtitle2" id="text-size" sx={{ mb: 1 }}>Text size</Typography>
              <ToggleButtonGroup
                exclusive fullWidth size="small" value={prefs.textScale} aria-labelledby="text-size"
                onChange={(_, v) => v && setPrefs({ textScale: v })}
              >
                <ToggleButton value={1}>Default</ToggleButton>
                <ToggleButton value={1.15}>Large</ToggleButton>
                <ToggleButton value={1.3}>Largest</ToggleButton>
              </ToggleButtonGroup>
              <Divider sx={{ my: 1.5 }} />
              <FormControlLabel
                control={<Switch checked={prefs.highContrast} onChange={(e) => setPrefs({ highContrast: e.target.checked })} />}
                label="High contrast"
              />
            </Box>
          </Menu>

          <Box sx={{ display: "flex", alignItems: "center", gap: 1.25 }}>
            <Box sx={{ textAlign: "right", lineHeight: 1.25, display: { xs: "none", sm: "block" } }}>
              <Typography variant="body2" sx={{ fontWeight: 700 }}>{user.fullName}</Typography>
              <Typography variant="caption" sx={{ fontWeight: 600 }}>
                {roleLabel[activeRole]}{discipline ? `, ${disciplineLabel[discipline]}` : ""}
              </Typography>
            </Box>
            <Box
              aria-hidden
              sx={{ width: 42, height: 42, borderRadius: "50%", bgcolor: utep.navy, color: "#fff", display: "grid", placeItems: "center", fontWeight: 700 }}
            >
              {initials}
            </Box>
            <Chip label="Training" size="small" sx={{ bgcolor: utep.navy, color: "#fff", display: { xs: "none", md: "flex" } }} />
          </Box>
        </Toolbar>
      </AppBar>
      <Box aria-hidden sx={{ height: 4, background: trainingStripe }} />
    </>
  );
}
