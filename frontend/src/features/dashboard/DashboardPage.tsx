import { Alert, Box, LinearProgress } from "@mui/material";
import { useSession } from "../auth/useSession";
import { usePageHeading } from "../../components/usePageHeading";
import StudentDashboard from "./StudentDashboard";
import InstructorDashboard from "./InstructorDashboard";

export default function DashboardPage() {
  const { activeRole } = useSession();
  usePageHeading("Dashboard");

  if (activeRole === "student") return <StudentDashboard />;
  if (activeRole === "instructor" || activeRole === "course_coordinator") return <InstructorDashboard />;

  return (
    <Box>
      <Alert severity="info">Use the sidebar to open patients, roster, or the activity log.</Alert>
      <LinearProgress sx={{ mt: 2, visibility: "hidden" }} />
    </Box>
  );
}
