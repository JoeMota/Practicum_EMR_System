import { useState } from "react";
import {
  Alert, Box, Button, Chip, FormControl, InputLabel, LinearProgress, MenuItem, Paper, Select, Stack, Typography,
} from "@mui/material";
import DownloadOutlined from "@mui/icons-material/DownloadOutlined";
import { downloadCourseReport, getCourseReport } from "../../api/reports";
import { listCoursesForUser } from "../../api/courses";
import { useSession } from "../auth/AuthContext";
import { usePageHeading } from "../../components/PageHeading";
import { useAsync } from "../../utils/useAsync";

const STATUS_LABELS: Record<string, string> = {
  draft: "Draft",
  pending_review: "Pending review",
  signed: "Signed",
  cosigned: "Co-signed",
  returned: "Returned",
};

function CountSection({ title, values, labels = {} }: { title: string; values: Record<string, number>; labels?: Record<string, string> }) {
  return (
    <Paper component="section" sx={{ p: 2.25 }}>
      <Typography component="h2" variant="subtitle1" sx={{ fontWeight: 700, mb: 1.5 }}>{title}</Typography>
      <Stack spacing={1}>
        {Object.entries(values).map(([key, value]) => (
          <Box key={key} sx={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 2 }}>
            <Typography variant="body2" color="text.secondary">{labels[key] ?? key.replaceAll("_", " ")}</Typography>
            <Chip size="small" label={value} />
          </Box>
        ))}
      </Stack>
    </Paper>
  );
}

export default function ReportsPage() {
  usePageHeading("Reports");
  const { user } = useSession();
  const courses = useAsync(() => listCoursesForUser(), [user.id]);
  const [courseId, setCourseId] = useState("");
  const [error, setError] = useState("");
  const report = useAsync(() => courseId ? getCourseReport(courseId) : Promise.resolve(undefined), [courseId]);
  const selected = courses.data?.find((course) => course.id === courseId);

  const download = async () => {
    if (!courseId) return;
    setError("");
    try {
      const csv = await downloadCourseReport(courseId);
      const url = URL.createObjectURL(new Blob([csv], { type: "text/csv;charset=utf-8" }));
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = `${selected?.code ?? "course"}-report.csv`;
      anchor.click();
      URL.revokeObjectURL(url);
    } catch (e) {
      setError((e as Error).message);
    }
  };

  return (
    <Stack spacing={2.5}>
      <Box>
        <Typography component="h1" variant="h5" sx={{ fontWeight: 700 }}>Course reports</Typography>
        <Typography variant="body2" color="text.secondary">Enrollment, clinical activity, and audit totals.</Typography>
      </Box>
      {error && <Alert severity="error" onClose={() => setError("")}>{error}</Alert>}

      <Stack direction={{ xs: "column", sm: "row" }} spacing={1.5} sx={{ alignItems: { sm: "center" } }}>
        <FormControl size="small" sx={{ minWidth: 260 }}>
          <InputLabel id="report-course-label">Course</InputLabel>
          <Select
            labelId="report-course-label" label="Course" value={courseId}
            onChange={(event) => setCourseId(event.target.value)}
          >
            {(courses.data ?? []).map((course) => (
              <MenuItem key={course.id} value={course.id}>{course.code}: {course.title}</MenuItem>
            ))}
          </Select>
        </FormControl>
        <Button variant="outlined" startIcon={<DownloadOutlined />} disabled={!courseId} onClick={download}>Download CSV</Button>
      </Stack>

      {report.loading && courseId && <LinearProgress />}
      {report.error && <Alert severity="error">{report.error.message}</Alert>}
      {report.data && (
        <>
          <Box sx={{ display: "grid", gap: 1.5, gridTemplateColumns: { xs: "1fr 1fr", md: "repeat(3, minmax(0, 1fr))" } }}>
            {[
              { label: "Students enrolled", count: report.data.studentsEnrolled },
              { label: "Patients", count: Object.values(report.data.patientsByMode).reduce((sum, count) => sum + count, 0) },
              { label: "Audit events", count: report.data.auditEventCount },
            ].map((stat) => (
              <Paper key={stat.label} sx={{ p: 2.25, borderTop: "3px solid", borderColor: "secondary.main" }}>
                <Typography variant="body2" color="text.secondary">{stat.label}</Typography>
                <Typography component="p" variant="h4" sx={{ fontWeight: 700, mt: 0.5 }}>{stat.count}</Typography>
              </Paper>
            ))}
          </Box>
          <Box sx={{ display: "grid", gap: 1.5, gridTemplateColumns: { xs: "1fr", md: "repeat(3, minmax(0, 1fr))" } }}>
            <CountSection title="Notes by status" values={report.data.notesByStatus} labels={STATUS_LABELS} />
            <CountSection title="Patients by mode" values={report.data.patientsByMode} />
            <CountSection title="Audit events by action" values={report.data.auditEventsByAction} />
          </Box>
        </>
      )}
      {!report.loading && !report.data && !report.error && (
        <Typography color="text.secondary">{courseId ? "No report data available." : "Select a course to view its report."}</Typography>
      )}
    </Stack>
  );
}
