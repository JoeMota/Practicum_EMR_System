import { useState, type FormEvent } from "react";
import {
  Alert, Box, Button, Chip, LinearProgress, Paper, Stack, Table, TableBody, TableCell, TableHead, TableRow,
  TextField, Typography,
} from "@mui/material";
import { createCourse, listCoursesForUser, setCourseStatus } from "../../api/courses";
import type { Course, CourseStatus } from "../../types";
import { useAsync } from "../../utils/useAsync";
import { useSession } from "../auth/AuthContext";
import { usePageHeading } from "../../components/PageHeading";

const statusTone: Record<CourseStatus, "default" | "info" | "success" | "warning"> = {
  planned: "info",
  active: "success",
  ended: "warning",
  archived: "default",
};

export default function CourseAdminPage() {
  usePageHeading("Courses");
  const { user } = useSession();
  const courses = useAsync(() => listCoursesForUser(), [user.id]);
  const [code, setCode] = useState("");
  const [title, setTitle] = useState("");
  const [term, setTerm] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const mutateStatus = async (course: Course, next: CourseStatus) => {
    setBusy(true);
    setError("");
    try {
      const updated = await setCourseStatus(course.id, next);
      courses.setData((current) => current?.map((item) => item.id === updated.id ? updated : item));
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  };

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      const created = await createCourse({ code: code.trim(), title: title.trim(), term: term.trim() });
      courses.setData((current) => [...(current ?? []), created].sort((a, b) => a.code.localeCompare(b.code)));
      setCode("");
      setTitle("");
      setTerm("");
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  };

  const actions = (course: Course) => {
    if (course.status === "planned") return <Button size="small" disabled={busy} onClick={() => mutateStatus(course, "active")}>Start</Button>;
    if (course.status === "active") return <Button size="small" color="warning" disabled={busy} onClick={() => mutateStatus(course, "ended")}>End</Button>;
    if (course.status === "ended") return (
      <Stack direction="row" spacing={0.5} sx={{ justifyContent: "flex-end" }}>
        <Button size="small" disabled={busy} onClick={() => mutateStatus(course, "active")}>Reopen</Button>
        <Button size="small" color="error" disabled={busy} onClick={() => mutateStatus(course, "archived")}>Archive</Button>
      </Stack>
    );
    return null;
  };

  return (
    <Stack spacing={2.5}>
      <Box>
        <Typography component="h1" variant="h5" sx={{ fontWeight: 700 }}>Course management</Typography>
        <Typography variant="body2" color="text.secondary">Create courses and manage their lifecycle.</Typography>
      </Box>
      {error && <Alert severity="error" onClose={() => setError("")}>{error}</Alert>}

      <Paper component="form" onSubmit={submit} sx={{ p: { xs: 2, md: 2.5 } }}>
        <Typography component="h2" variant="h6" sx={{ mb: 1.5 }}>Create course</Typography>
        <Stack direction={{ xs: "column", md: "row" }} spacing={1.5} sx={{ alignItems: { md: "flex-start" } }}>
          <TextField size="small" label="Course code" value={code} onChange={(e) => setCode(e.target.value)} required slotProps={{ htmlInput: { maxLength: 30 } }} />
          <TextField size="small" label="Title" value={title} onChange={(e) => setTitle(e.target.value)} required fullWidth slotProps={{ htmlInput: { maxLength: 200 } }} />
          <TextField size="small" label="Term" value={term} onChange={(e) => setTerm(e.target.value)} required slotProps={{ htmlInput: { maxLength: 40 } }} />
          <Button type="submit" variant="contained" disabled={busy}>Create</Button>
        </Stack>
      </Paper>

      <Paper>
        {courses.loading && <LinearProgress />}
        <Box sx={{ px: 2.5, pt: 2 }}>
          <Typography component="h2" variant="h6">Courses ({courses.data?.length ?? 0})</Typography>
        </Box>
        <Box sx={{ overflowX: "auto", p: 1 }}>
          <Table size="small">
            <TableHead>
              <TableRow><TableCell>Code</TableCell><TableCell>Title</TableCell><TableCell>Term</TableCell><TableCell>Status</TableCell><TableCell align="right">Actions</TableCell></TableRow>
            </TableHead>
            <TableBody>
              {(courses.data ?? []).map((course) => (
                <TableRow key={course.id}>
                  <TableCell sx={{ fontWeight: 700, whiteSpace: "nowrap" }}>{course.code}</TableCell>
                  <TableCell>{course.title}</TableCell>
                  <TableCell>{course.term}</TableCell>
                  <TableCell><Chip size="small" label={course.status} color={statusTone[course.status]} /></TableCell>
                  <TableCell align="right">{actions(course)}</TableCell>
                </TableRow>
              ))}
              {!courses.loading && courses.data?.length === 0 && (
                <TableRow><TableCell colSpan={5} sx={{ color: "text.secondary" }}>No courses yet.</TableCell></TableRow>
              )}
            </TableBody>
          </Table>
        </Box>
      </Paper>
    </Stack>
  );
}
