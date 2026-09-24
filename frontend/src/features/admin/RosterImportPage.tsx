import { useRef, useState, type FormEvent } from "react";
import {
  Alert, Box, Button, Chip, Dialog, DialogActions, DialogContent, DialogContentText, DialogTitle,
  LinearProgress, Link, MenuItem, Paper, Stack, Table, TableBody, TableCell, TableHead, TableRow,
  TextField, Typography,
} from "@mui/material";
import UploadFileOutlined from "@mui/icons-material/UploadFileOutlined";
import PersonAddAlt1Outlined from "@mui/icons-material/PersonAddAlt1Outlined";
import type { Discipline, RosterRow, User } from "../../types";
import { addRosterMember, importRoster, listRoster, removeFromCourse } from "../../api/roster";
import { getCourse } from "../../api/courses";
import { useSession } from "../auth/AuthContext";
import { disciplineLabel, roleLabel } from "../../utils/labels";
import { useAsync } from "../../utils/useAsync";
import EmptyState from "../../components/EmptyState";
import { parseRosterFile, ROSTER_TEMPLATE_CSV } from "./parseRoster";

type AppRole = "student" | "instructor";

const EMPTY_FORM = {
  fullName: "",
  email: "",
  universityId: "",
  discipline: "pharmacy" as Discipline,
  appRole: "student" as AppRole,
};

export default function RosterImportPage() {
  const { user, courseId } = useSession();
  const fileInput = useRef<HTMLInputElement>(null);
  const [rows, setRows] = useState<RosterRow[]>();
  const [fileName, setFileName] = useState("");
  const [discipline, setDiscipline] = useState<Discipline>("pharmacy");
  const [form, setForm] = useState(EMPTY_FORM);
  const [message, setMessage] = useState<{ kind: "success" | "error"; text: string }>();
  const [removing, setRemoving] = useState<User>();
  const [busyImport, setBusyImport] = useState(false);
  const [busyAdd, setBusyAdd] = useState(false);
  const [busyRemove, setBusyRemove] = useState(false);

  const course = useAsync(() => getCourse(courseId), [courseId]);
  const roster = useAsync(() => listRoster(courseId), [courseId]);

  const problems = rows?.filter((r) => r.problem).length ?? 0;
  const templateHref = `data:text/csv;charset=utf-8,${encodeURIComponent(ROSTER_TEMPLATE_CSV)}`;
  const loading = course.loading || roster.loading;

  const onFile = async (file?: File) => {
    if (!file) return;
    setMessage(undefined);
    try {
      const parsed = await parseRosterFile(file);
      setRows(parsed);
      setFileName(file.name);
      if (parsed.length === 0) {
        setMessage({ kind: "error", text: "No student rows found. The first sheet needs Name, Email, and 800 Number columns." });
      }
    } catch {
      setMessage({ kind: "error", text: "That file couldn't be read. Upload an .xlsx, .xls, or .csv file." });
    }
  };

  const doImport = async () => {
    if (!rows) return;
    setBusyImport(true);
    setMessage(undefined);
    try {
      const res = await importRoster(user, courseId, discipline, rows);
      setMessage({
        kind: "success",
        text: `Added ${res.added} students to ${course.data?.code ?? "the course"}.${res.alreadyEnrolled ? ` ${res.alreadyEnrolled} were already enrolled.` : ""}`,
      });
      setRows(undefined);
      setFileName("");
      roster.reload();
    } catch (e) {
      setMessage({ kind: "error", text: (e as Error).message });
    } finally {
      setBusyImport(false);
    }
  };

  const doAddOne = async (e: FormEvent) => {
    e.preventDefault();
    if (!form.fullName.trim() || !form.email.trim()) {
      setMessage({ kind: "error", text: "Name and UTEP email are required." });
      return;
    }
    setBusyAdd(true);
    setMessage(undefined);
    try {
      const res = await addRosterMember(user, courseId, {
        fullName: form.fullName,
        email: form.email,
        universityId: form.universityId || undefined,
        discipline: form.discipline,
        appRole: form.appRole,
      });
      const who = res.user.fullName;
      if (res.alreadyEnrolled) {
        setMessage({ kind: "success", text: `${who} is already on this course roster.` });
      } else if (res.created) {
        setMessage({
          kind: "success",
          text: `Added ${who}. Temporary password is ChangeMe1! — they'll change it on first sign-in.`,
        });
      } else {
        setMessage({ kind: "success", text: `Enrolled ${who} in this course.` });
      }
      setForm(EMPTY_FORM);
      roster.reload();
    } catch (err) {
      setMessage({ kind: "error", text: (err as Error).message });
    } finally {
      setBusyAdd(false);
    }
  };

  const roleFor = (u: User): string => {
    const onCourse = u.roles.filter((r) => r.courseIds.includes(courseId));
    if (onCourse.some((r) => r.role === "instructor")) return roleLabel.instructor;
    if (onCourse.some((r) => r.role === "student")) return roleLabel.student;
    return onCourse[0] ? roleLabel[onCourse[0].role] : "—";
  };

  const disciplineFor = (u: User): string => {
    const d = u.roles.find((r) => r.role === "student" && r.courseIds.includes(courseId))?.discipline;
    return d ? disciplineLabel[d] : "—";
  };

  return (
    <Stack spacing={2.5} sx={{ animation: "emrFadeIn 220ms ease-out" }}>
      <Box>
        <Typography component="h1" variant="h5">Course roster</Typography>
        <Typography variant="body2" color="text.secondary">
          {course.data ? `${course.data.code}: ${course.data.title}, ${course.data.term}` : "Loading course…"}
        </Typography>
      </Box>

      {loading && <LinearProgress aria-label="Loading roster" />}
      {(course.error || roster.error) && (
        <Alert severity="error">{course.error?.message || roster.error?.message}</Alert>
      )}
      {message && (
        <Alert severity={message.kind} onClose={() => setMessage(undefined)}>{message.text}</Alert>
      )}

      <Paper sx={{ p: { xs: 2, sm: 2.5 } }}>
        <Stack direction="row" spacing={1} sx={{ alignItems: "center", mb: 0.5 }}>
          <PersonAddAlt1Outlined color="primary" fontSize="small" />
          <Typography component="h2" variant="h6">Add one person</Typography>
        </Stack>
        <Typography variant="body2" color="text.secondary" sx={{ mb: 2, maxWidth: "70ch" }}>
          Instructors and admins can add a student or instructor by UTEP email. New accounts start with temporary
          password <strong>ChangeMe1!</strong> and must change it on first login.
        </Typography>
        <Box component="form" noValidate onSubmit={doAddOne}>
          <Stack spacing={1.75}>
            <Stack direction={{ xs: "column", sm: "row" }} spacing={1.5}>
              <TextField
                label="Full name" required fullWidth size="small"
                value={form.fullName}
                onChange={(e) => setForm((f) => ({ ...f, fullName: e.target.value }))}
                autoComplete="name"
              />
              <TextField
                label="UTEP email" type="email" required fullWidth size="small"
                placeholder="name@miners.utep.edu"
                value={form.email}
                onChange={(e) => setForm((f) => ({ ...f, email: e.target.value }))}
                autoComplete="email"
              />
            </Stack>
            <Stack direction={{ xs: "column", sm: "row" }} spacing={1.5}>
              <TextField
                label="800 number" fullWidth size="small"
                placeholder="800123456"
                value={form.universityId}
                onChange={(e) => setForm((f) => ({ ...f, universityId: e.target.value.replace(/\D/g, "").slice(0, 9) }))}
                helperText="Optional for instructors"
              />
              <TextField
                select size="small" label="Role in this course" fullWidth
                value={form.appRole}
                onChange={(e) => setForm((f) => ({ ...f, appRole: e.target.value as AppRole }))}
              >
                <MenuItem value="student">Student</MenuItem>
                <MenuItem value="instructor">Instructor</MenuItem>
              </TextField>
              {form.appRole === "student" && (
                <TextField
                  select size="small" label="Discipline" fullWidth
                  value={form.discipline}
                  onChange={(e) => setForm((f) => ({ ...f, discipline: e.target.value as Discipline }))}
                >
                  {(Object.keys(disciplineLabel) as Discipline[]).map((d) => (
                    <MenuItem key={d} value={d}>{disciplineLabel[d]}</MenuItem>
                  ))}
                </TextField>
              )}
            </Stack>
            <Box>
              <Button type="submit" variant="contained" disabled={busyAdd || loading} startIcon={<PersonAddAlt1Outlined />}>
                {busyAdd ? "Adding…" : "Add to course"}
              </Button>
            </Box>
          </Stack>
        </Box>
      </Paper>

      <Paper sx={{ p: { xs: 2, sm: 2.5 } }}>
        <Typography component="h2" variant="h6">Add students from a spreadsheet</Typography>
        <Typography variant="body2" color="text.secondary" sx={{ mb: 2, maxWidth: "70ch" }}>
          Upload an Excel or CSV with name, UTEP email, and 800 number. Existing accounts are reused and enrolled in
          this course. <Link href={templateHref} download="roster-template.csv">Download a template</Link>.
        </Typography>

        <Stack direction={{ xs: "column", sm: "row" }} spacing={1.5} sx={{ alignItems: { sm: "center" } }}>
          <TextField
            select size="small" label="Students' discipline" value={discipline}
            onChange={(e) => setDiscipline(e.target.value as Discipline)} sx={{ minWidth: 240 }}
          >
            {(Object.keys(disciplineLabel) as Discipline[]).map((d) => (
              <MenuItem key={d} value={d}>{disciplineLabel[d]}</MenuItem>
            ))}
          </TextField>
          <input
            ref={fileInput} type="file" hidden accept=".xlsx,.xls,.csv"
            onChange={(e) => { onFile(e.target.files?.[0]); e.target.value = ""; }}
          />
          <Button variant="outlined" startIcon={<UploadFileOutlined />} onClick={() => fileInput.current?.click()}>
            {fileName ? "Choose a different file" : "Choose file"}
          </Button>
          {fileName && <Typography variant="body2">{fileName}</Typography>}
        </Stack>

        {rows && rows.length > 0 && (
          <Box sx={{ mt: 2.5 }}>
            <Box sx={{ display: "flex", gap: 1, alignItems: "center", mb: 1, flexWrap: "wrap" }}>
              <Chip label={`${rows.length} rows`} size="small" />
              {problems > 0 && <Chip label={`${problems} need fixing`} size="small" color="error" />}
              <Box sx={{ flex: 1 }} />
              {problems > 0 && (
                <Button size="small" onClick={() => setRows(rows.filter((r) => !r.problem))}>
                  Skip rows with problems
                </Button>
              )}
              <Button variant="contained" disabled={problems > 0 || busyImport} onClick={doImport}>
                {busyImport ? "Importing…" : `Add ${rows.length} students`}
              </Button>
            </Box>
            <Box sx={{ overflowX: "auto", maxHeight: 360 }}>
              <Table size="small" stickyHeader>
                <TableHead>
                  <TableRow>
                    <TableCell>Name</TableCell>
                    <TableCell>Email</TableCell>
                    <TableCell>800 number</TableCell>
                    <TableCell>Check</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {rows.map((r, i) => (
                    <TableRow key={`${r.email}-${i}`} sx={r.problem ? { bgcolor: "#FEF3F2" } : undefined}>
                      <TableCell>{r.fullName || "—"}</TableCell>
                      <TableCell>{r.email || "—"}</TableCell>
                      <TableCell>{r.universityId || "—"}</TableCell>
                      <TableCell sx={{ color: r.problem ? "error.main" : "success.main", fontWeight: 600 }}>
                        {r.problem ?? "Ready"}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </Box>
          </Box>
        )}
      </Paper>

      <Paper sx={{ p: { xs: 2, sm: 2.5 } }}>
        <Typography component="h2" variant="h6">
          People on this course ({roster.data?.length ?? 0})
        </Typography>
        <Typography variant="body2" color="text.secondary" sx={{ mb: 1.5 }}>
          Remove someone at term end. Their account stays available for other courses; signed notes remain.
        </Typography>
        {(roster.data ?? []).length === 0 && !roster.loading ? (
          <EmptyState title="No one enrolled yet">Add one person above, or upload a roster spreadsheet.</EmptyState>
        ) : (
          <Box sx={{ overflowX: "auto" }}>
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell>Name</TableCell>
                  <TableCell>Email</TableCell>
                  <TableCell>800 number</TableCell>
                  <TableCell>Role</TableCell>
                  <TableCell>Discipline</TableCell>
                  <TableCell />
                </TableRow>
              </TableHead>
              <TableBody>
                {roster.data?.map((u) => (
                  <TableRow key={u.id} hover>
                    <TableCell sx={{ fontWeight: 600 }}>{u.fullName}</TableCell>
                    <TableCell>{u.email}</TableCell>
                    <TableCell>{u.universityId ?? "—"}</TableCell>
                    <TableCell>{roleFor(u)}</TableCell>
                    <TableCell>{disciplineFor(u)}</TableCell>
                    <TableCell align="right">
                      <Button size="small" color="error" onClick={() => setRemoving(u)}>Remove</Button>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </Box>
        )}
      </Paper>

      <Dialog open={Boolean(removing)} onClose={() => !busyRemove && setRemoving(undefined)}>
        <DialogTitle>Remove {removing?.fullName} from {course.data?.code}?</DialogTitle>
        <DialogContent>
          <DialogContentText>
            They lose access to this course&apos;s patients. Their signed notes stay in the record.
          </DialogContentText>
        </DialogContent>
        <DialogActions>
          <Button disabled={busyRemove} onClick={() => setRemoving(undefined)}>Cancel</Button>
          <Button
            color="error"
            variant="contained"
            disabled={busyRemove}
            onClick={async () => {
              setBusyRemove(true);
              try {
                await removeFromCourse(user, courseId, removing!.id);
                setRemoving(undefined);
                roster.reload();
              } catch (err) {
                setMessage({ kind: "error", text: (err as Error).message });
                setRemoving(undefined);
              } finally {
                setBusyRemove(false);
              }
            }}
          >
            {busyRemove ? "Removing…" : "Remove"}
          </Button>
        </DialogActions>
      </Dialog>
    </Stack>
  );
}
