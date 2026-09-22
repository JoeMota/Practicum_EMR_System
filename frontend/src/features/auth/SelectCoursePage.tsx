import { useState } from "react";
import {
  Box, Button, Card, CardActionArea, CardContent, Chip, Stack, ToggleButton, ToggleButtonGroup, Typography,
} from "@mui/material";
import { useNavigate } from "react-router-dom";
import { listCoursesForUser } from "../../api/courses";
import { disciplineLabel, roleLabel } from "../../utils/labels";
import { homePathFor } from "../../utils/permissions";
import { useAsync } from "../../utils/useAsync";
import { trainingStripe, utep } from "../../theme/tokens";
import { useSession } from "./AuthContext";

/** "After selecting a class, students will see patient cases assigned to that class." */
export default function SelectCoursePage() {
  const navigate = useNavigate();
  const { user, activeRole, switchRole, selectCourse, signOut } = useSession();
  const [picked, setPicked] = useState<string>();
  const { data: courses = [], loading, error } = useAsync(() => listCoursesForUser(user), [user.id]);

  const assignment = user.roles.find((r) => r.role === activeRole);
  const available = courses.filter((c) => assignment?.courseIds.includes(c.id));

  const go = () => {
    if (!picked) return;
    selectCourse(picked);
    navigate(homePathFor(activeRole), { replace: true });
  };

  return (
    <Box sx={{ minHeight: "100dvh", bgcolor: "background.default" }}>
      <Box sx={{ bgcolor: utep.orange, color: utep.navy, px: 3.5, height: 60, display: "flex", alignItems: "center" }}>
        <Typography sx={{ fontWeight: 800, fontSize: 18 }}>UTEP EMR</Typography>
        <Box sx={{ flex: 1 }} />
        <Button color="inherit" onClick={signOut}>Sign out</Button>
      </Box>
      <Box aria-hidden sx={{ height: 6, background: trainingStripe }} />

      <Box component="main" sx={{ maxWidth: 640, mx: "auto", px: 2, py: 5 }}>
        <Typography component="h1" variant="h5">Welcome, {user.fullName.split(" ")[0]}</Typography>
        <Typography color="text.secondary" sx={{ mb: 3 }}>Choose the course you're working in today.</Typography>

        {error && <Typography color="error" sx={{ mb: 2 }}>{error.message}</Typography>}

        {user.roles.length > 1 && (
          <Box sx={{ mb: 3 }}>
            <Typography variant="subtitle2" id="role-label" sx={{ mb: 1 }}>Sign in as</Typography>
            <ToggleButtonGroup
              exclusive value={activeRole} aria-labelledby="role-label" size="small"
              onChange={(_, r) => { if (r) { switchRole(r); setPicked(undefined); } }}
            >
              {user.roles.map((r) => (
                <ToggleButton key={r.role} value={r.role} sx={{ px: 2 }}>{roleLabel[r.role]}</ToggleButton>
              ))}
            </ToggleButtonGroup>
          </Box>
        )}

        <Stack spacing={1.5} role="radiogroup" aria-label="Courses">
          {available.map((c) => (
            <Card
              key={c.id}
              sx={{ borderColor: picked === c.id ? "primary.main" : undefined, borderWidth: picked === c.id ? 2 : 1 }}
            >
              <CardActionArea role="radio" aria-checked={picked === c.id} onClick={() => setPicked(c.id)} onDoubleClick={go}>
                <CardContent sx={{ display: "flex", alignItems: "center", gap: 2 }}>
                  <Box sx={{ flex: 1 }}>
                    <Typography variant="subtitle1">{c.code}: {c.title}</Typography>
                    <Typography variant="body2" color="text.secondary">{c.term}</Typography>
                  </Box>
                  {assignment?.discipline && <Chip size="small" label={disciplineLabel[assignment.discipline]} />}
                </CardContent>
              </CardActionArea>
            </Card>
          ))}
          {!loading && available.length === 0 && (
            <Typography color="text.secondary">
              You aren't on any course roster yet. Ask your instructor to add you.
            </Typography>
          )}
          {loading && <Typography color="text.secondary">Loading your courses…</Typography>}
        </Stack>

        <Button variant="contained" size="large" sx={{ mt: 3 }} disabled={!picked} onClick={go}>
          Open course
        </Button>
      </Box>
    </Box>
  );
}
