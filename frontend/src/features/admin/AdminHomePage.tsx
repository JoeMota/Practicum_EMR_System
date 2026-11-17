import { Box, Button, LinearProgress, Paper, Stack, Typography } from "@mui/material";
import { Link as RouterLink } from "react-router-dom";
import { listCoursesForUser } from "../../api/courses";
import { useSession } from "../auth/useSession";
import { useAsync } from "../../utils/useAsync";
import { usePageHeading } from "../../components/usePageHeading";

export default function AdminHomePage() {
  usePageHeading("Administration");
  const { user } = useSession();
  const courses = useAsync(() => listCoursesForUser(), [user.id]);
  const count = courses.data?.length;

  return (
    <Stack spacing={2.5}>
      <Box>
        <Typography variant="body2" color="text.secondary" sx={{ maxWidth: "62ch" }}>
          Classes and accounts. Instructors build cases and grade notes in their own screens.
        </Typography>
      </Box>
      {courses.loading && <LinearProgress aria-label="Loading classes" />}
      <Box sx={{ display: "grid", gap: 2, gridTemplateColumns: { xs: "1fr", md: "1fr 1fr" } }}>
        <Paper sx={{ p: 2.5 }}>
          <Typography component="h2" variant="h6">Classes</Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5, mb: 2 }}>
            {count === undefined ? " " : `${count} ${count === 1 ? "class" : "classes"} on file. Create one and set whether it is planned, active, ended, or archived.`}
          </Typography>
          <Button component={RouterLink} to="/admin/courses" variant="contained">Manage classes</Button>
        </Paper>
        <Paper sx={{ p: 2.5 }}>
          <Typography component="h2" variant="h6">People</Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5, mb: 2 }}>
            Enroll students, add instructors, and add course coordinators. Student accounts stay with the administrator for the whole program.
          </Typography>
          <Button component={RouterLink} to="/admin/people" variant="contained">Manage people</Button>
        </Paper>
      </Box>
    </Stack>
  );
}
