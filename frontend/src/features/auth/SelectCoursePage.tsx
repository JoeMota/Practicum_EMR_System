import { useState } from "react";
import { flushSync } from "react-dom";
import {
  Box, Button, Stack, ToggleButton, ToggleButtonGroup, Typography,
} from "@mui/material";
import CheckCircleRounded from "@mui/icons-material/CheckCircleRounded";
import { useNavigate } from "react-router-dom";
import { listCoursesForUser } from "../../api/courses";
import { disciplineLabel, roleLabel } from "../../utils/labels";
import { courseIdsForRole, homePathFor, uniqueRoles } from "../../utils/permissions";
import { useAsync } from "../../utils/useAsync";
import BrandLogo from "../../components/BrandLogo";
import { brandAtmosphere, fontDisplay, utep } from "../../theme/tokens";
import { useSession } from "./useSession";

export default function SelectCoursePage() {
  const navigate = useNavigate();
  const { user, activeRole, switchRole, selectCourse, signOut } = useSession();
  const [pickedId, setPickedId] = useState<string>();
  const { data: courses = [], loading, error } = useAsync(() => listCoursesForUser(), [user.id]);

  const assignment = user.roles.find((r) => r.role === activeRole);
  const roles = uniqueRoles(user);
  const roleCourseIds = courseIdsForRole(user, activeRole);
  const available = activeRole === "admin"
    ? courses
    : courses.filter((c) => roleCourseIds.includes(c.id) && (activeRole !== "student" || c.status !== "ended"));

  const soleId = available.length === 1 ? available[0].id : undefined;
  const picked = pickedId && available.some((c) => c.id === pickedId) ? pickedId : soleId;

  const go = () => {
    if (!picked) return;
    flushSync(() => selectCourse(picked));
    navigate(homePathFor(activeRole), { replace: true });
  };

  return (
    <Box
      sx={{
        minHeight: "100dvh",
        display: "grid",
        gridTemplateColumns: { xs: "1fr", md: "minmax(0, 0.9fr) minmax(340px, 520px)" },
        bgcolor: utep.navyDark,
      }}
    >
      <Box
        sx={{
          display: { xs: "none", md: "flex" },
          flexDirection: "column",
          justifyContent: "flex-end",
          px: 7,
          py: 7,
          backgroundImage: brandAtmosphere,
          color: "#fff",
          position: "relative",
          "&::after": {
            content: '""',
            position: "absolute",
            inset: 0,
            background: "linear-gradient(180deg, transparent 40%, rgba(8,22,54,0.5) 100%)",
            pointerEvents: "none",
          },
        }}
      >
        <Box sx={{ position: "relative", zIndex: 1 }}>
          <BrandLogo variant="hero" titleSize={48} />
          <Box sx={{ width: 64, height: 3, bgcolor: utep.orange, my: 2 }} />
          <Typography sx={{ opacity: 0.85, maxWidth: "28ch" }}>
            Pick the role and course for this session.
          </Typography>
          <Box sx={{ mt: 4, maxWidth: 240, opacity: 0.9 }}>
            <BrandLogo variant="wordmark" />
          </Box>
        </Box>
      </Box>

      <Box
        component="main"
        sx={{
          bgcolor: utep.paper,
          px: { xs: 3, sm: 4 },
          py: { xs: 4, md: 6 },
          display: "flex",
          flexDirection: "column",
          minHeight: "100dvh",
        }}
      >
        <Box sx={{ display: "flex", alignItems: "center", mb: 3 }}>
          <Typography sx={{ fontFamily: fontDisplay, fontWeight: 800, fontSize: 20, color: utep.navy, display: { md: "none" } }}>
            UTEP EMR
          </Typography>
          <Box sx={{ flex: 1 }} />
          <Button onClick={signOut} size="small">Sign out</Button>
        </Box>

        <Typography component="h1" variant="h5" sx={{ mb: 0.75 }}>
          Welcome, {user.fullName.split(" ")[0]}
        </Typography>
        <Typography color="text.secondary" sx={{ mb: 3, maxWidth: "42ch" }}>
          {activeRole === "admin"
            ? "Administration is separate from teaching."
            : "Choose the course you're working in today."}
          {activeRole === "student" && " You'll see the patients and cases assigned to that class."}
          {(activeRole === "instructor" || activeRole === "course_coordinator") && " You'll review notes and teach that class."}
        </Typography>

        {roles.length > 1 && (
          <Box sx={{ mb: 3 }}>
            <Typography variant="subtitle2" id="role-label" sx={{ mb: 1 }}>Sign in as</Typography>
            <ToggleButtonGroup
              exclusive value={activeRole} aria-labelledby="role-label" size="small"
              onChange={(_, r) => { if (r) { switchRole(r); setPickedId(undefined); } }}
            >
              {roles.map((role) => (
                <ToggleButton key={role} value={role} sx={{ px: 2, borderRadius: "4px !important" }}>{roleLabel[role]}</ToggleButton>
              ))}
            </ToggleButtonGroup>
          </Box>
        )}

        {activeRole === "admin" ? (
          <Box>
            <Typography color="text.secondary" sx={{ mb: 2, maxWidth: "48ch" }}>
              Add classes, enroll students, and add instructors. Case building and grading stay on the instructor screens.
            </Typography>
            <Button variant="contained" size="large" onClick={() => navigate("/admin")}>Open administration</Button>
          </Box>
        ) : (
          <>
            <Stack spacing={1} role="radiogroup" aria-label="Courses">
              {available.map((c) => {
                const selected = picked === c.id;
                return (
                  <Box
                    key={c.id}
                    component="button"
                    type="button"
                    role="radio"
                    aria-checked={selected}
                    onClick={() => setPickedId(c.id)}
                    onDoubleClick={go}
                    sx={{
                      display: "flex",
                      alignItems: "center",
                      gap: 2,
                      width: "100%",
                      textAlign: "left",
                      cursor: "pointer",
                      px: 2,
                      py: 1.75,
                      borderRadius: 1,
                      border: "none",
                      bgcolor: selected ? "rgba(14,34,80,0.06)" : "transparent",
                      boxShadow: selected ? `inset 3px 0 0 ${utep.orange}` : `inset 0 0 0 1px ${utep.lineSoft}`,
                      fontFamily: "inherit",
                      color: "inherit",
                      transition: "background-color 160ms ease, box-shadow 160ms ease",
                      "&:hover": { bgcolor: "rgba(14,34,80,0.04)" },
                      "&:focus-visible": { outline: `3px solid ${utep.navy}`, outlineOffset: 2 },
                    }}
                  >
                    <Box sx={{ flex: 1, minWidth: 0 }}>
                      <Typography variant="subtitle1" sx={{ lineHeight: 1.25 }}>{c.code}: {c.title}</Typography>
                      <Typography variant="body2" color="text.secondary">
                        {c.term}
                        {assignment?.discipline ? ` · ${disciplineLabel[assignment.discipline]}` : ""}
                        {` · ${c.status}`}
                      </Typography>
                    </Box>
                    {selected && <CheckCircleRounded color="primary" aria-hidden />}
                  </Box>
                );
              })}
              {error && <Typography color="error">{error.message}</Typography>}
              {loading && <Typography color="text.secondary">Loading your courses…</Typography>}
              {!loading && available.length === 0 && (
                <Typography color="text.secondary">
                  You aren't on any course roster yet. Ask your instructor to add you.
                </Typography>
              )}
            </Stack>

            <Button variant="contained" size="large" sx={{ mt: 3, alignSelf: "flex-start" }} disabled={!picked} onClick={go}>
              {picked ? "Open course" : "Select a course to continue"}
            </Button>
          </>
        )}
      </Box>
    </Box>
  );
}
