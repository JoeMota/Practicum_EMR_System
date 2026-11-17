import { useRef, useState } from "react";
import {
  Alert, Box, Button, Chip, Dialog, DialogActions, DialogContent, DialogContentText, DialogTitle, Link,
  MenuItem, Paper, Stack, Table, TableBody, TableCell, TableHead, TableRow, TextField, Typography,
} from "@mui/material";
import UploadFileOutlined from "@mui/icons-material/UploadFileOutlined";
import type { Discipline, RosterRow, User } from "../../types";
import { importRoster, listRoster, removeFromCourse, setRosterActive, type TempPassword } from "../../api/roster";
import { getCourse, listInstructors } from "../../api/courses";
import { archiveUser, deleteAccount, purgeExpiredAccounts, resetPassword, setUserActive } from "../../api/users";
import EditAccountDialog from "./EditAccountDialog";
import { useSession } from "../auth/useSession";
import { can } from "../../utils/permissions";
import { disciplineLabel, roleLabel } from "../../utils/labels";
import { useAsync } from "../../utils/useAsync";
import EmptyState from "../../components/EmptyState";
import { usePageHeading } from "../../components/usePageHeading";
import { parseRosterFile, ROSTER_TEMPLATE_CSV } from "./parseRoster";
import AddPersonForm from "./AddPersonForm";
import EnrollAccount from "./EnrollAccount";

export default function RosterImportPage({ courseId: courseIdProp }: { courseId?: string }) {
  usePageHeading(courseIdProp ? "People" : "Roster");
  const { user, activeRole, courseId: sessionCourseId } = useSession();
  const courseId = courseIdProp ?? sessionCourseId;
  const fileInput = useRef<HTMLInputElement>(null);
  const [rows, setRows] = useState<RosterRow[]>();
  const [fileName, setFileName] = useState("");
  const [discipline, setDiscipline] = useState<Discipline>("pharmacy");
  const manageStudents = can(activeRole, "roster:import");
  const [importRole, setImportRole] = useState<"student" | "instructor" | "course_coordinator">(manageStudents ? "student" : "instructor");
  const [message, setMessage] = useState<{ kind: "success" | "error"; text: string }>();
  const [passwords, setPasswords] = useState<TempPassword[]>([]);
  const [removing, setRemoving] = useState<{ person: User; role: "student" | "instructor" | "course_coordinator" }>();
  const [editing, setEditing] = useState<User>();
  const [deleting, setDeleting] = useState<User>();
  const [confirmEmail, setConfirmEmail] = useState("");

  const course = useAsync(() => (courseId ? getCourse(courseId) : Promise.resolve(undefined)), [courseId]);
  const roster = useAsync(
    () => (manageStudents && courseId ? listRoster(courseId) : Promise.resolve([])),
    [courseId, manageStudents],
  );
  const instructors = useAsync(() => (courseId ? listInstructors(courseId) : Promise.resolve([])), [courseId]);

  const problems = rows?.filter((r) => r.problem).length ?? 0;
  const templateHref = `data:text/csv;charset=utf-8,${encodeURIComponent(ROSTER_TEMPLATE_CSV)}`;

  const onFile = async (file?: File) => {
    if (!file) return;
    setMessage(undefined);
    try {
      const parsed = await parseRosterFile(file);
      const ready = importRole === "student"
        ? parsed
        : parsed.map((row) => ({ ...row, problem: row.problem === "ID must be a 9-digit 800 number" ? undefined : row.problem }));
      setRows(ready);
      setFileName(file.name);
      if (ready.length === 0) setMessage({ kind: "error", text: "No rows found. The first sheet needs a name and a UTEP email." });
    } catch {
      setMessage({ kind: "error", text: "That file couldn't be read. Upload an .xlsx, .xls, or .csv file." });
    }
  };

  const issuePassword = async (person: User) => {
    try {
      const issued = await resetPassword(person.id);
      setPasswords([issued]);
      setMessage({ kind: "success", text: `A temporary password was issued for ${person.fullName}.` });
    } catch (e) {
      setMessage({ kind: "error", text: (e as Error).message });
    }
  };

  const doImport = async (list = rows): Promise<boolean> => {
    if (!list || !courseId) return false;
    try {
      const res = await importRoster(courseId, discipline, list, importRole);
      setPasswords(res.temporaryPasswords);
      const extras = [
        res.reactivated ? `${res.reactivated} reactivated` : "",
        res.alreadyEnrolled ? `${res.alreadyEnrolled} already enrolled` : "",
      ].filter(Boolean);
      setMessage({
        kind: "success",
        text: `Added ${res.added} ${importRole}s to ${course.data?.code}${extras.length ? `. ${extras.join(". ")}.` : "."}`,
      });
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

  if (!courseId) return null;

  return (
    <Stack spacing={2.5}>
      {!courseIdProp && (
        <Typography variant="body2" color="text.secondary">
          {course.data ? `${course.data.code}: ${course.data.title}, ${course.data.term}` : "Enroll people in this class."}
        </Typography>
      )}

      {message && <Alert severity={message.kind} onClose={() => setMessage(undefined)}>{message.text}</Alert>}
      {passwords.length > 0 && (
        <Alert severity="warning">
          Share these temporary passwords. They have to change them at sign-in, and this is the only time they show up.
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
          {manageStudents && (
            <TextField select size="small" label="Add as" value={importRole} onChange={(e) => setImportRole(e.target.value as "student" | "instructor" | "course_coordinator")} sx={{ minWidth: 200 }}>
              <MenuItem value="student">Student</MenuItem>
              <MenuItem value="instructor">Instructor</MenuItem>
              <MenuItem value="course_coordinator">Course coordinator</MenuItem>
            </TextField>
          )}
          <TextField select size="small" label="Discipline" value={discipline} onChange={(e) => setDiscipline(e.target.value as Discipline)} sx={{ minWidth: 240 }}>
            {(Object.keys(disciplineLabel) as Discipline[]).map((d) => <MenuItem key={d} value={d}>{disciplineLabel[d]}</MenuItem>)}
          </TextField>
        </Stack>

        <Stack direction={{ xs: "column", md: "row" }} spacing={3} sx={{ mt: 2.5 }}>
          {activeRole === "admin" && courseId && (
            <EnrollAccount
              courseId={courseId}
              role={importRole}
              discipline={discipline}
              onEnrolled={() => {
                roster.reload();
                instructors.reload();
                setMessage({ kind: "success", text: `Enrolled in ${course.data?.code ?? "this class"}.` });
              }}
            />
          )}
          <Box sx={{ flex: 1, minWidth: 0 }}>
            <Typography component="h3" variant="subtitle1" sx={{ fontWeight: 600 }}>
              {activeRole === "admin" ? "Or create an account" : "Add one person"}
            </Typography>
            <AddPersonForm
              role={importRole}
              discipline={discipline}
              onSubmit={(row) => doImport([row])}
            />
          </Box>

          <Box sx={{ flex: 1, minWidth: 0 }}>
            <Typography component="h3" variant="subtitle1" sx={{ fontWeight: 600, mb: 1 }}>Or upload a spreadsheet</Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 1.5 }}>
              Upload Excel or CSV. Students need a name, UTEP email, and 800 number. Instructors need a name and UTEP email. Existing accounts are enrolled. <Link href={templateHref} download="roster-template.csv">Download a template</Link>.
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

      {manageStudents && <Paper sx={{ p: 2.5 }}>
        <Typography component="h2" variant="h6">Enrolled students ({roster.data?.length ?? 0})</Typography>
        <Typography variant="body2" color="text.secondary" sx={{ mb: 1.5 }}>
          Deactivate keeps the student on the roster and keeps their charts and notes. They lose access until you reactivate them. Remove deletes the enrollment.
        </Typography>
        {(roster.data ?? []).length === 0 ? (
          <EmptyState title="No students yet">Upload a roster to add your class.</EmptyState>
        ) : (
          <Box sx={{ overflowX: "auto" }}>
            <Table size="small">
              <TableHead>
                <TableRow><TableCell>Name</TableCell><TableCell>Email</TableCell><TableCell>800 number</TableCell><TableCell>Discipline</TableCell><TableCell>Access</TableCell><TableCell /></TableRow>
              </TableHead>
              <TableBody>
                {roster.data?.map((u) => {
                  const d = u.roles.find((r) => r.role === "student" && r.courseIds.includes(courseId))?.discipline;
                  const inactive = u.rosterStatus === "inactive";
                  return (
                    <TableRow key={u.id}>
                      <TableCell sx={{ fontWeight: 600 }}>{u.fullName}</TableCell>
                      <TableCell>{u.email}</TableCell>
                      <TableCell>{u.universityId ?? "—"}</TableCell>
                      <TableCell>{d ? disciplineLabel[d] : "—"}</TableCell>
                      <TableCell><Chip size="small" label={inactive ? "Inactive" : "Active"} color={inactive ? "default" : "success"} /></TableCell>
                      <TableCell align="right">
                        <Button size="small" color="warning" onClick={async () => {
                          try {
                            const updated = await setRosterActive(courseId, u.id, inactive);
                            roster.setData((current) => current?.map((item) => item.id === u.id ? updated : item));
                          } catch (e) {
                            setMessage({ kind: "error", text: (e as Error).message });
                          }
                        }}>{inactive ? "Reactivate" : "Deactivate"}</Button>
                        {manageStudents && (
                          <Button size="small" onClick={async () => {
                            try {
                              await archiveUser(u.id);
                              roster.reload();
                              setMessage({ kind: "success", text: `${u.fullName} was archived. The account is kept for two years, then an administrator can purge it.` });
                            } catch (e) {
                              setMessage({ kind: "error", text: (e as Error).message });
                            }
                          }}>Archive</Button>
                        )}
                        {activeRole === "admin" && (
                          <Button size="small" disabled={u.id === user.id && u.isActive} onClick={async () => {
                            try {
                              await setUserActive(u.id, !u.isActive);
                              roster.setData((current) => current?.map((item) => item.id === u.id ? { ...item, isActive: !u.isActive } : item));
                            } catch (e) {
                              setMessage({ kind: "error", text: (e as Error).message });
                            }
                          }}>{u.isActive ? "Deactivate account" : "Reactivate account"}</Button>
                        )}
                        {activeRole === "admin" && <Button size="small" onClick={() => setEditing(u)}>Edit</Button>}
                        {activeRole === "admin" && (
                          <Button size="small" disabled={u.id === user.id} onClick={() => issuePassword(u)}>Reset password</Button>
                        )}
                        {activeRole === "admin" && (
                          <Button size="small" color="error" disabled={u.id === user.id} onClick={() => { setConfirmEmail(""); setDeleting(u); }}>Delete account</Button>
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
      </Paper>}

      {manageStudents && (
        <Button variant="outlined" onClick={async () => {
          try {
            const result = await purgeExpiredAccounts();
            setMessage({ kind: "success", text: `${result.purged} archived account${result.purged === 1 ? "" : "s"} passed the two-year mark and ${result.purged === 1 ? "was" : "were"} purged.` });
          } catch (e) {
            setMessage({ kind: "error", text: (e as Error).message });
          }
        }}>Purge accounts archived more than two years</Button>
      )}

      <Paper sx={{ p: 2.5 }}>
        <Typography component="h2" variant="h6">Instructors ({instructors.data?.length ?? 0})</Typography>
        <Typography variant="body2" color="text.secondary" sx={{ mb: 1.5 }}>At least one instructor must remain assigned to the course.</Typography>
        {(instructors.data ?? []).length === 0 ? (
          <EmptyState title="No instructors assigned">Add an instructor from the import form.</EmptyState>
        ) : (
          <Box sx={{ overflowX: "auto" }}>
            <Table size="small">
              <TableHead><TableRow><TableCell>Name</TableCell><TableCell>Email</TableCell><TableCell>Role in this class</TableCell><TableCell>Account</TableCell><TableCell /></TableRow></TableHead>
              <TableBody>
                {instructors.data?.map((person) => {
                  const teaching = person.roles.flatMap((item) =>
                    (item.role === "instructor" || item.role === "course_coordinator") && item.courseIds.includes(courseId) ? [item.role] : [],
                  );
                  const roles = teaching.length > 0 ? teaching : ["instructor" as const];
                  return (
                  <TableRow key={person.id}>
                    <TableCell sx={{ fontWeight: 600 }}>{person.fullName}</TableCell>
                    <TableCell>{person.email}</TableCell>
                    <TableCell>
                      <Stack direction="row" spacing={0.5} sx={{ flexWrap: "wrap" }}>
                        {roles.map((role) => <Chip key={role} size="small" label={roleLabel[role]} />)}
                      </Stack>
                    </TableCell>
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
                      {activeRole === "admin" && <Button size="small" onClick={() => setEditing(person)}>Edit</Button>}
                      {activeRole === "admin" && (
                        <Button size="small" disabled={person.id === user.id} onClick={() => issuePassword(person)}>Reset password</Button>
                      )}
                      {activeRole === "admin" && (
                        <Button size="small" color="error" disabled={person.id === user.id} onClick={() => { setConfirmEmail(""); setDeleting(person); }}>Delete account</Button>
                      )}
                      {roles.filter((role) => role !== "course_coordinator" || activeRole === "admin").map((role) => (
                        <Button key={role} size="small" color="error" disabled={person.id === user.id} onClick={() => setRemoving({ person, role })}>
                          Remove {roleLabel[role].toLowerCase()}
                        </Button>
                      ))}
                    </TableCell>
                  </TableRow>
                  );
                })}
              </TableBody>
            </Table>
          </Box>
        )}
      </Paper>

      <EditAccountDialog
        key={editing?.id}
        person={editing}
        requireStudentId={Boolean(editing?.roles.some((item) => item.role === "student"))}
        onClose={() => setEditing(undefined)}
        onSaved={(updated) => {
          const merge = (item: User) => item.id === updated.id ? { ...item, ...updated, rosterStatus: item.rosterStatus } : item;
          roster.setData((current) => current?.map(merge));
          instructors.setData((current) => current?.map(merge));
          setMessage({ kind: "success", text: `${updated.fullName}'s account was updated.` });
        }}
      />

      <Dialog open={Boolean(deleting)} onClose={() => setDeleting(undefined)}>
        <DialogTitle>Delete {deleting?.fullName}'s account?</DialogTitle>
        <DialogContent>
          <DialogContentText sx={{ mb: 2 }}>
            The login stops working and class memberships are removed. Charts and notes stay so the grade record remains. Type {deleting?.email} to confirm.
          </DialogContentText>
          <TextField
            autoFocus
            fullWidth
            label="Email"
            value={confirmEmail}
            onChange={(event) => setConfirmEmail(event.target.value)}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDeleting(undefined)}>Cancel</Button>
          <Button
            color="error"
            variant="contained"
            disabled={!deleting || confirmEmail.trim().toLowerCase() !== deleting.email.toLowerCase()}
            onClick={async () => {
              const target = deleting!;
              try {
                await deleteAccount(target.id, confirmEmail.trim());
                roster.reload();
                instructors.reload();
                setMessage({ kind: "success", text: `${target.fullName}'s login was removed. Charts and notes were kept.` });
              } catch (e) {
                setMessage({ kind: "error", text: (e as Error).message });
              }
              setDeleting(undefined);
            }}
          >Delete account</Button>
        </DialogActions>
      </Dialog>

      <Dialog open={Boolean(removing)} onClose={() => setRemoving(undefined)}>
        <DialogTitle>Remove {removing?.person.fullName} from {course.data?.code}?</DialogTitle>
        <DialogContent>
          <DialogContentText>
            Remove deletes this enrollment. Deactivate is the reversible choice: it keeps their charts and notes and only turns access off.
          </DialogContentText>
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
