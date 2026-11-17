import { useRef, useState } from "react";
import { Alert, Box, Button, Paper, Stack, Table, TableBody, TableCell, TableHead, TableRow, TextField, Typography } from "@mui/material";
import { downloadChartTime, downloadGrades, getActivity, getCourse, uploadGradingGuide } from "../../api/courses";
import { useSession } from "../auth/useSession";
import { can } from "../../utils/permissions";
import { useAsync } from "../../utils/useAsync";
import { formatDateTime } from "../../utils/format";
import { usePageHeading } from "../../components/usePageHeading";
import CourseRubricPanel from "../encounters/components/CourseRubricPanel";
import NoteTemplateAuthor from "../encounters/components/NoteTemplateAuthor";

function iso(day: Date) {
  const month = String(day.getMonth() + 1).padStart(2, "0");
  const date = String(day.getDate()).padStart(2, "0");
  return `${day.getFullYear()}-${month}-${date}`;
}

export default function TeachingPage() {
  usePageHeading("Grades and time");
  const { activeRole, courseId } = useSession();
  const course = useAsync(() => getCourse(courseId), [courseId]);
  const fileInput = useRef<HTMLInputElement>(null);
  const [caseKey, setCaseKey] = useState("");
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [start, setStart] = useState(() => {
    const day = new Date();
    day.setDate(day.getDate() - 30);
    return iso(day);
  });
  const [end, setEnd] = useState(() => iso(new Date()));
  const activity = useAsync(
    () => getActivity(courseId, activeRole, start, end),
    [courseId, activeRole, start, end],
  );
  const canUpload = can(activeRole, "case:author") || can(activeRole, "course:manage_access");

  return (
    <Stack spacing={2}>
      <Typography variant="body2" color="text.secondary">
        Excel exports for this course. Case masters are not included. Blackboard is not connected.
      </Typography>
      {message && <Alert severity="success" onClose={() => setMessage("")}>{message}</Alert>}
      {error && <Alert severity="error" onClose={() => setError("")}>{error}</Alert>}
      <Paper sx={{ p: 2.5 }}>
        <Typography component="h2" variant="h6">Rubric</Typography>
        <CourseRubricPanel guide={course.data?.gradingGuide} fileName={course.data?.rubricFileName} />
        {canUpload && (
          <>
            <input ref={fileInput} hidden type="file" accept=".pdf,.docx" onChange={async (event) => {
              const file = event.target.files?.[0];
              event.target.value = "";
              if (!file) return;
              setError("");
              try {
                course.setData(await uploadGradingGuide(courseId, file));
                setMessage(`${file.name} was converted into scoring criteria.`);
              } catch (e) {
                setError((e as Error).message);
              }
            }} />
            <Button sx={{ mt: 1.5 }} variant="outlined" onClick={() => fileInput.current?.click()}>Upload PDF or Word rubric</Button>
          </>
        )}
      </Paper>
      <Paper sx={{ p: 2.5 }}>
        <Typography component="h2" variant="h6" sx={{ mb: 1.5 }}>Grade export</Typography>
        <TextField label="Case key" value={caseKey} onChange={(e) => setCaseKey(e.target.value)} helperText="The case key from the case you assigned." sx={{ mr: 1, mb: 1 }} />
        <Button variant="contained" disabled={!caseKey.trim()} onClick={async () => {
          setError("");
          try { await downloadGrades(courseId, activeRole, caseKey.trim()); }
          catch (e) { setError((e as Error).message); }
        }}>Download grades</Button>
      </Paper>
      <Paper sx={{ p: 2.5 }}>
        <Typography component="h2" variant="h6" sx={{ mb: 1 }}>Student activity</Typography>
        <Typography variant="body2" color="text.secondary" sx={{ mb: 1.5 }}>
          One row per student. Minutes count while the chart is open and the student is active.
        </Typography>
        <Stack direction={{ xs: "column", sm: "row" }} spacing={1.5} sx={{ mb: 2, alignItems: { sm: "center" } }}>
          <TextField size="small" type="date" label="From" value={start} onChange={(e) => setStart(e.target.value)} slotProps={{ inputLabel: { shrink: true } }} />
          <TextField size="small" type="date" label="To" value={end} onChange={(e) => setEnd(e.target.value)} slotProps={{ inputLabel: { shrink: true } }} />
          <Button variant="outlined" disabled={!start || !end} onClick={async () => {
            setError("");
            try { await downloadChartTime(courseId, activeRole, start, end); }
            catch (e) { setError((e as Error).message); }
          }}>Download Excel</Button>
        </Stack>
        {activity.error && <Alert severity="error" sx={{ mb: 1.5 }}>{activity.error.message}</Alert>}
        <Box sx={{ overflowX: "auto" }}>
          <Table size="small" aria-label="Student activity">
            <TableHead>
              <TableRow>
                <TableCell>Student</TableCell>
                <TableCell>Last sign-in</TableCell>
                <TableCell align="right">Sessions</TableCell>
                <TableCell align="right">Active minutes</TableCell>
                <TableCell align="right">Charts opened</TableCell>
                <TableCell align="right">Notes started</TableCell>
                <TableCell align="right">Notes submitted</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {(activity.data?.rows ?? []).map((row) => (
                <TableRow key={row.userId}>
                  <TableCell>{row.student}</TableCell>
                  <TableCell>{row.lastSignIn ? formatDateTime(row.lastSignIn) : "—"}</TableCell>
                  <TableCell align="right">{row.sessions}</TableCell>
                  <TableCell align="right">{row.activeMinutes}</TableCell>
                  <TableCell align="right">{row.chartsOpened}</TableCell>
                  <TableCell align="right">{row.notesStarted}</TableCell>
                  <TableCell align="right">{row.notesSubmitted}</TableCell>
                </TableRow>
              ))}
              {!activity.loading && (activity.data?.rows.length ?? 0) === 0 && (
                <TableRow><TableCell colSpan={7}>No students on this roster.</TableCell></TableRow>
              )}
            </TableBody>
          </Table>
        </Box>
      </Paper>
      <NoteTemplateAuthor role={activeRole} courseId={courseId} />
    </Stack>
  );
}
