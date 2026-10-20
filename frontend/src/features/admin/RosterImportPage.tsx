import { useRef, useState } from "react";
import {
  Alert, Box, Button, Chip, Dialog, DialogActions, DialogContent, DialogContentText, DialogTitle, Link,
  MenuItem, Paper, Stack, Table, TableBody, TableCell, TableHead, TableRow, TextField, Typography,
} from "@mui/material";
import UploadFileOutlined from "@mui/icons-material/UploadFileOutlined";
import type { Discipline, RosterRow, User } from "../../types";
import { importRoster, listRoster, removeFromCourse, type TempPassword } from "../../api/roster";
import { getCourse, listInstructors } from "../../api/courses";
import { setUserActive } from "../../api/users";
import { useSession } from "../auth/AuthContext";
import { disciplineLabel } from "../../utils/labels";
import { useAsync } from "../../utils/useAsync";
import EmptyState from "../../components/EmptyState";
import { usePageHeading } from "../../components/PageHeading";
import { parseRosterFile, ROSTER_TEMPLATE_CSV } from "./parseRoster";
import AddPersonForm from "./AddPersonForm";

export default function RosterImportPage() {
  usePageHeading("Roster");
  const { user, activeRole, courseId } = useSession();
  const fileInput = useRef<HTMLInputElement>(null);
  const [rows, setRows] = useState<RosterRow[]>();
  const [fileName, setFileName] = useState("");
  const [discipline, setDiscipline] = useState<Discipline>("pharmacy");
  const [importRole, setImportRole] = useState<"student" | "instructor">("student");
  const [message, setMessage] = useState<{ kind: "success" | "error"; text: string }>();
  const [passwords, setPasswords] = useState<TempPassword[]>([]);
  const [removing, setRemoving] = useState<{ person: User; role: "student" | "instructor" }>();

  const course = useAsync(() => getCourse(courseId), [courseId]);
  const roster = useAsync(() => listRoster(courseId), [courseId]);
  const instructors = useAsync(() => listInstructors(courseId), [courseId]);

  const problems = rows?.filter((r) => r.problem).length ?? 0;
  const templateHref = `data:text/csv;charset=utf-8,${encodeURIComponent(ROSTER_TEMPLATE_CSV)}`;

  const onFile = async (file?: File) => {
    if (!file) return;
    setMessage(undefined);
    try {
      const parsed = await parseRosterFile(file);
      setRows(parsed);
      setFileName(file.name);
      if (parsed.length === 0) setMessage({ kind: "error", text: "No student rows found. The first sheet needs Name, Email, and 800 Number columns." });
    } catch {
      setMessage({ kind: "error", text: "That file couldn't be read. Upload an .xlsx, .xls, or .csv file." });
    }
  };

  const doImport = async (list = rows): Promise<boolean> => {
    if (!list) return false;
    try {
      const res = await importRoster(courseId, discipline, list, importRole);
      setPasswords(res.temporaryPasswords);
      setMessage({ kind: "success", text: `Added ${res.added} ${importRole}s to ${course.data?.code}.${res.alreadyEnrolled ? ` ${res.alreadyEnrolled} were already enrolled.` : ""}` });
      if (list === rows) {
        setRows(undefined);
        setFileName("");
      }
      roster.reload();
      instructors.reload();
      return true;
    } catch (e) {
      setMessage({ kind: "error", text: (e as Error).message });
      return false;
    }
  };

  return (
    <Stack spacing={2.5}>
      <Box>
        <Typography variant="h5" sx={{ fontWeight: 700 }}>Course roster</Typography>
        <Typography variant="body2" color="text.secondary">{course.data ? `${course.data.code}: ${course.data.title}, ${course.data.term}` : " "}</Typography>
      </Box>

      {message && <Alert severity={message.kind} onClose={() => setMessage(undefined)}>{message.text}</Alert>}
      {passwords.length > 0 && (
        <Alert severity="warning">
          Share these temporary passwords with the new students. They have to change them at sign-in, and this is the only time they show up.
          <Box component="ul" sx={{ mt: 1, mb: 0, pl: 2 }}>
            {passwords.map((item) => (
              <li key={item.email}><strong>{item.email}</strong>: {item.password}</li>
            ))}
          </Box>
        </Alert>
      )}

      <Paper sx={{ p: 2.5 }}>
        <Typography component="h2" variant="h6">Add people</Typography>
        <Stack direction={{ xs: "column", sm: "row" }} spacing={1.5} sx={{ alignItems: { sm: "center" }, mt: 2 }}>
          {activeRole === "admin" && (
            <TextField select size="small" label="Add as" value={importRole} onChange={(e) => setImportRole(e.target.value as "student" | "instructor")} sx={{ minWidth: 160 }}>
              <MenuItem value="student">Student</MenuItem>
              <MenuItem value="instructor">Instructor</MenuItem>
            </TextField>
          )}
          <TextField select size="small" label="Discipline" value={discipline} onChange={(e) => setDiscipline(e.target.value as Discipline)} sx={{ minWidth: 240 }}>
            {(Object.keys(disciplineLabel) as Discipline[]).map((d) => <MenuItem key={d} value={d}>{disciplineLabel[d]}</MenuItem>)}
          </TextField>
        </Stack>

        <Stack direction={{ xs: "column", md: "row" }} spacing={3} sx={{ mt: 2.5 }}>
          <Box sx={{ flex: 1, minWidth: 0 }}>
            <Typography component="h3" variant="subtitle1" sx={{ fontWeight: 600 }}>Add one person</Typography>
            <AddPersonForm
              role={activeRole === "admin" ? importRole : "student"}
              discipline={discipline}
              onSubmit={(row) => doImport([row])}
            />
          </Box>

          <Box sx={{ flex: 1, minWidth: 0 }}>
            <Typography component="h3" variant="subtitle1" sx={{ fontWeight: 600, mb: 1 }}>Or upload a spreadsheet</Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 1.5 }}>
              Upload Excel or CSV with name, UTEP email, and 800 number; existing accounts are added. <Link href={templateHref} download="roster-template.csv">Download a template</Link>.
            </Typography>
          <input ref={fileInput} type="file" hidden accept=".xlsx,.xls,.csv" onChange={(e) => { onFile(e.target.files?.[0]); e.target.value = ""; }} />
          <Button variant="outlined" startIcon={<UploadFileOutlined />} onClick={() => fileInput.current?.click()}>
            {fileName ? "Choose a different file" : "Choose file"}
          </Button>
          {fileName && <Typography variant="body2">{fileName}</Typography>}
          </Box>
        </Stack>
      </Paper>

      {rows && rows.length > 0 && (
          <Box sx={{ mt: 2.5 }}>
            <Box sx={{ display: "flex", gap: 1, alignItems: "center", mb: 1, flexWrap: "wrap" }}>
              <Chip label={`${rows.length} rows`} size="small" />
              {problems > 0 && <Chip label={`${problems} need fixing`} size="small" color="error" />}
              <Box sx={{ flex: 1 }} />
              {problems > 0 && (
                <Button size="small" onClick={() => setRows(rows.filter((r) => !r.problem))}>Skip rows with problems</Button>
              )}
              <Button variant="contained" disabled={problems > 0} onClick={() => doImport()}>
                Add {rows.length} {importRole === "student" ? "students" : "instructors"}
              </Button>
            </Box>
            <Box sx={{ overflowX: "auto", maxHeight: 360 }}>
              <Table size="small" stickyHeader>
                <TableHead>
                  <TableRow><TableCell>Name</TableCell><TableCell>Email</TableCell><TableCell>800 number</TableCell><TableCell>Check</TableCell></TableRow>
                </TableHead>
                <TableBody>
                  {rows.map((r, i) => (
                    <TableRow key={`${r.email}-${i}`} sx={r.problem ? { bgcolor: "#FEF3F2" } : undefined}>
                      <TableCell>{r.fullName || "—"}</TableCell>
                      <TableCell>{r.email || "—"}</TableCell>
                      <TableCell>{r.universityId || "—"}</TableCell>
                      <TableCell sx={{ color: r.problem ? "error.main" : "success.main", fontWeight: 600 }}>{r.problem ?? "Ready"}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </Box>
          </Box>
      )}

      <Paper sx={{ p: 2.5 }}>
        <Typography component="h2" variant="h6">Enrolled students ({roster.data?.length ?? 0})</Typography>
        <Typography variant="body2" color="text.secondary" sx={{ mb: 1.5 }}>
          Remove a student if they leave the course. Their account and signed notes stay; they just lose access to this class.
          Deactivate / reactivate without removing is planned next — for now, re-import restores access.
        </Typography>
        {(roster.data ?? []).length === 0 ? (
          <EmptyState title="No students yet">Upload a roster to add your class.</EmptyState>
        ) : (
          <Box sx={{ overflowX: "auto" }}>
            <Table size="small">
              <TableHead>
                <TableRow><TableCell>Name</TableCell><TableCell>Email</TableCell><TableCell>800 number</TableCell><TableCell>Discipline</TableCell><TableCell /></TableRow>
              </TableHead>
              <TableBody>
                {roster.data?.map((u) => {
                  const d = u.roles.find((r) => r.role === "student" && r.courseIds.includes(courseId))?.discipline;
                  return (
                    <TableRow key={u.id}>
                      <TableCell sx={{ fontWeight: 600 }}>{u.fullName}</TableCell>
                      <TableCell>{u.email}</TableCell>
                      <TableCell>{u.universityId ?? "—"}</TableCell>
                      <TableCell>{d ? disciplineLabel[d] : "—"}</TableCell>
                      <TableCell align="right">
                        {activeRole === "admin" && (
                          <Button size="small" color="warning" disabled={u.id === user.id && u.isActive} onClick={async () => {
                            try {
                              await setUserActive(u.id, !u.isActive);
                              roster.setData((current) => current?.map((item) => item.id === u.id ? { ...item, isActive: !u.isActive } : item));
                            } catch (e) {
                              setMessage({ kind: "error", text: (e as Error).message });
                            }
                          }}>{u.isActive ? "Deactivate" : "Reactivate"}</Button>
                        )}
                        <Button size="small" color="error" onClick={() => setRemoving({ person: u, role: "student" })}>Remove</Button>
                      </TableCell>
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
          </Box>
        )}
      </Paper>

      <Paper sx={{ p: 2.5 }}>
        <Typography component="h2" variant="h6">Instructors ({instructors.data?.length ?? 0})</Typography>
        <Typography variant="body2" color="text.secondary" sx={{ mb: 1.5 }}>At least one instructor must remain assigned to the course.</Typography>
        {(instructors.data ?? []).length === 0 ? (
          <EmptyState title="No instructors assigned">Add an instructor from the import form.</EmptyState>
        ) : (
          <Box sx={{ overflowX: "auto" }}>
            <Table size="small">
              <TableHead><TableRow><TableCell>Name</TableCell><TableCell>Email</TableCell><TableCell>Account</TableCell><TableCell /></TableRow></TableHead>
              <TableBody>
                {instructors.data?.map((person) => (
                  <TableRow key={person.id}>
                    <TableCell sx={{ fontWeight: 600 }}>{person.fullName}</TableCell>
                    <TableCell>{person.email}</TableCell>
                    <TableCell>{person.isActive ? "Active" : "Inactive"}</TableCell>
                    <TableCell align="right">
                      {activeRole === "admin" && (
                        <Button size="small" color="warning" disabled={person.id === user.id && person.isActive} onClick={async () => {
                          try {
                            await setUserActive(person.id, !person.isActive);
                            instructors.setData((current) => current?.map((item) => item.id === person.id ? { ...item, isActive: !person.isActive } : item));
                          } catch (e) {
                            setMessage({ kind: "error", text: (e as Error).message });
                          }
                        }}>{person.isActive ? "Deactivate" : "Reactivate"}</Button>
                      )}
                      <Button size="small" color="error" disabled={person.id === user.id} onClick={() => setRemoving({ person, role: "instructor" })}>Remove</Button>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </Box>
        )}
      </Paper>

      <Dialog open={Boolean(removing)} onClose={() => setRemoving(undefined)}>
        <DialogTitle>Remove {removing?.person.fullName} from {course.data?.code}?</DialogTitle>
        <DialogContent>
          <DialogContentText>They lose access to this course's patients. Their signed notes stay in the record.</DialogContentText>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setRemoving(undefined)}>Cancel</Button>
          <Button color="error" variant="contained" onClick={async () => {
            const target = removing!;
            try {
              await removeFromCourse(courseId, target.person.id, target.role);
              if (target.role === "student") roster.reload();
              else instructors.reload();
            } catch (e) {
              setMessage({ kind: "error", text: (e as Error).message });
            }
            setRemoving(undefined);
          }}>Remove {removing?.role}</Button>
        </DialogActions>
      </Dialog>
    </Stack>
  );
}
