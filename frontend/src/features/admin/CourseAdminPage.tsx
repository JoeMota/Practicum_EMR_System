import { useState, type FormEvent } from "react";
import {
  Alert, Box, Button, Chip, LinearProgress, Paper, Stack, Table, TableBody, TableCell, TableHead, TableRow,
  MenuItem, Switch, TextField, Typography,
} from "@mui/material";
import { createCourse, downloadAllActivity, listCoursesForUser, setCoursePolicy, setCourseStatus, setInactivityDays } from "../../api/courses";
import type { Course, CourseStatus } from "../../types";
import { useAsync } from "../../utils/useAsync";
import { useSession } from "../auth/useSession";
import { usePageHeading } from "../../components/usePageHeading";
import NoteTemplateAuthor from "../encounters/components/NoteTemplateAuthor";

const statusTone: Record<CourseStatus, "default" | "info" | "success" | "warning"> = {
  planned: "info",
  active: "success",
  ended: "warning",
  archived: "default",
};

export default function CourseAdminPage() {
  usePageHeading("Classes");
  const { user } = useSession();
  const courses = useAsync(() => listCoursesForUser(), [user.id]);
  const [code, setCode] = useState("");
  const [title, setTitle] = useState("");
  const [term, setTerm] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [start, setStart] = useState(() => {
    const day = new Date();
    day.setDate(day.getDate() - 30);
    const month = String(day.getMonth() + 1).padStart(2, "0");
    return `${day.getFullYear()}-${month}-${String(day.getDate()).padStart(2, "0")}`;
  });
  const [end, setEnd] = useState(() => {
    const day = new Date();
    const month = String(day.getMonth() + 1).padStart(2, "0");
    return `${day.getFullYear()}-${month}-${String(day.getDate()).padStart(2, "0")}`;
  });

  const savePolicy = async (course: Course, patch: Parameters<typeof setCoursePolicy>[1]) => {
    setBusy(true);
    setError("");
    try {
      const updated = await setCoursePolicy(course.id, patch);
      courses.setData((current) => current?.map((item) => item.id === updated.id ? updated : item));
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  };

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
    if (course.status === "archived") return <Button size="small" disabled={busy} onClick={() => mutateStatus(course, "active")}>Retrieve</Button>;
    return null;
  };

  const saveDays = async (course: Course, value: string) => {
    const days = Number(value);
    if (!Number.isInteger(days) || days < 1 || days > 90 || days === course.inactivityDays) return;
    setBusy(true);
    setError("");
    try {
      const updated = await setInactivityDays(course.id, days);
      courses.setData((current) => current?.map((item) => item.id === updated.id ? updated : item));
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <Stack spacing={2.5}>
      <Box>
        <Typography variant="body2" color="text.secondary">Create a class, set the at-risk window, and retrieve an archived class.</Typography>
      </Box>
      {error && <Alert severity="error" onClose={() => setError("")}>{error}</Alert>}

      <Paper component="form" onSubmit={submit} sx={{ p: { xs: 2, md: 2.5 } }}>
        <Typography component="h2" variant="h6" sx={{ mb: 1.5 }}>Add a class</Typography>
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
          <Typography component="h2" variant="h6">Classes ({courses.data?.length ?? 0})</Typography>
        </Box>
        <Box sx={{ overflowX: "auto", p: 1 }}>
          <Table size="small">
            <TableHead>
              <TableRow><TableCell>Code</TableCell><TableCell>Title</TableCell><TableCell>Term</TableCell><TableCell>Status</TableCell><TableCell>At-risk days</TableCell><TableCell>Dose check</TableCell><TableCell align="right">Actions</TableCell></TableRow>
            </TableHead>
            <TableBody>
              {(courses.data ?? []).map((course) => (
                <TableRow key={course.id}>
                  <TableCell sx={{ fontWeight: 700, whiteSpace: "nowrap" }}>{course.code}</TableCell>
                  <TableCell>{course.title}</TableCell>
                  <TableCell>{course.term}</TableCell>
                  <TableCell><Chip size="small" label={course.status} color={statusTone[course.status]} /></TableCell>
                  <TableCell>
                    <TextField
                      key={`${course.id}-${course.inactivityDays ?? 7}`}
                      size="small"
                      type="number"
                      defaultValue={course.inactivityDays ?? 7}
                      disabled={busy}
                      onBlur={(event) => saveDays(course, event.target.value)}
                      slotProps={{ htmlInput: { min: 1, max: 90, "aria-label": `Days without chart activity for ${course.code}` } }}
                      sx={{ width: 88 }}
                    />
                  </TableCell>
                  <TableCell>
                    <Stack direction="row" spacing={1}>
                      <TextField
                        select size="small" label="Profile" value={course.guardrailProfile ?? "practicum"} disabled={busy}
                        onChange={(event) => savePolicy(course, { guardrailProfile: event.target.value as Course["guardrailProfile"] })}
                        sx={{ minWidth: 140 }}
                      >
                        <MenuItem value="intro_pharmacy">Intro to Pharmacy</MenuItem>
                        <MenuItem value="practicum">Practicum</MenuItem>
                        <MenuItem value="clinical_other">Other clinical</MenuItem>
                      </TextField>
                      <TextField
                        select size="small" label="Mode" value={course.guardrailMode ?? ""} disabled={busy}
                        onChange={(event) => savePolicy(course, { guardrailMode: (event.target.value || null) as Course["guardrailMode"] })}
                        sx={{ minWidth: 130 }}
                      >
                        <MenuItem value="">Profile default</MenuItem>
                        <MenuItem value="off">Off</MenuItem>
                        <MenuItem value="advisory">Advisory</MenuItem>
                        <MenuItem value="acknowledge">Acknowledge</MenuItem>
                        <MenuItem value="block">Block</MenuItem>
                      </TextField>
                      <Switch
                        checked={Boolean(course.aiAssist)}
                        disabled={busy}
                        slotProps={{ input: { "aria-label": `Section assist for ${course.code}` } }}
                        onChange={(event) => savePolicy(course, { aiAssist: event.target.checked })}
                      />
                    </Stack>
                  </TableCell>
                  <TableCell align="right">{actions(course)}</TableCell>
                </TableRow>
              ))}
              {!courses.loading && courses.data?.length === 0 && (
                <TableRow><TableCell colSpan={8} sx={{ color: "text.secondary" }}>No courses yet.</TableCell></TableRow>
              )}
            </TableBody>
          </Table>
        </Box>
      </Paper>

      <Paper sx={{ p: 2.5 }}>
        <Typography component="h2" variant="h6">Activity for every class</Typography>
        <Typography variant="body2" color="text.secondary" sx={{ mb: 1.5 }}>
          One workbook with a row per student in each class. Case charts are not included.
        </Typography>
        <Stack direction={{ xs: "column", sm: "row" }} spacing={1.5} sx={{ alignItems: { sm: "center" } }}>
          <TextField size="small" type="date" label="From" value={start} onChange={(e) => setStart(e.target.value)} slotProps={{ inputLabel: { shrink: true } }} />
          <TextField size="small" type="date" label="To" value={end} onChange={(e) => setEnd(e.target.value)} slotProps={{ inputLabel: { shrink: true } }} />
          <Button variant="outlined" disabled={!start || !end} onClick={async () => {
            setError("");
            try { await downloadAllActivity(start, end); }
            catch (e) { setError((e as Error).message); }
          }}>Download Excel</Button>
        </Stack>
      </Paper>
      <NoteTemplateAuthor role="admin" />
    </Stack>
  );
}
