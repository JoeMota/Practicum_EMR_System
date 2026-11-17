import { useRef, useState } from "react";
import { Alert, Box, Button, Dialog, DialogActions, DialogContent, DialogTitle, LinearProgress, Menu, MenuItem, Paper, Table, TableBody, TableCell, TableHead, TableRow, TextField, Typography } from "@mui/material";
import { useNavigate } from "react-router-dom";
import { copyCase, downloadCaseTemplate, importCases, listCases } from "../../api/cases";
import { listCoursesForUser } from "../../api/courses";
import { useSession } from "../auth/useSession";
import { useAsync } from "../../utils/useAsync";
import { formatDateTime } from "../../utils/format";
import { courseIdsForRole } from "../../utils/permissions";
import { usePageHeading } from "../../components/usePageHeading";
import EmptyState from "../../components/EmptyState";
import PageError from "../../components/PageError";
import AssignCaseDialog from "../patients/components/AssignCaseDialog";
import StartSimulationDialog from "./StartSimulationDialog";
import type { AuthoredCase } from "../../types";

export default function CaseListPage() {
  usePageHeading("Cases");
  const navigate = useNavigate();
  const { activeRole, courseId } = useSession();
  const cases = useAsync(() => listCases(activeRole, courseId), [activeRole, courseId]);
  const [assignCase, setAssignCase] = useState<AuthoredCase>();
  const [simCase, setSimCase] = useState<AuthoredCase>();
  const [copyTarget, setCopyTarget] = useState<AuthoredCase>();
  const [rowMenu, setRowMenu] = useState<{ anchor: HTMLElement; item: AuthoredCase }>();
  const [notice, setNotice] = useState("");
  const fileInput = useRef<HTMLInputElement>(null);

  if (cases.error) return <PageError error={cases.error} />;

  return (
    <Box>
      <Box sx={{ display: "flex", alignItems: "flex-start", gap: 2, mb: 2, flexWrap: "wrap" }}>
        <Box sx={{ flex: 1, minWidth: 220 }}>
          <Typography variant="body2" color="text.secondary">
            Build a case once, then assign private copies. Later edits stay on the master.
          </Typography>
        </Box>
        <Button onClick={() => downloadCaseTemplate(activeRole, courseId)}>Download template</Button>
        <input ref={fileInput} hidden type="file" accept=".xlsx" onChange={async (event) => {
          const file = event.target.files?.[0];
          event.target.value = "";
          if (!file) return;
          try {
            const result = await importCases(activeRole, courseId, file);
            setNotice(`${result.created} case${result.created === 1 ? "" : "s"} imported.`);
            cases.reload();
          } catch (e) {
            setNotice((e as Error).message);
          }
        }} />
        <Button onClick={() => fileInput.current?.click()}>Upload cases</Button>
        <Button variant="contained" onClick={() => navigate("/cases/new")}>Create case</Button>
      </Box>

      {notice && <Alert severity="info" sx={{ mb: 2 }} onClose={() => setNotice("")}>{notice}</Alert>}
      {cases.loading && <LinearProgress aria-label="Loading cases" />}

      {!cases.loading && (cases.data ?? []).length === 0 ? (
        <EmptyState title="No cases yet" action={<Button variant="contained" onClick={() => navigate("/cases/new")}>Create case</Button>}>
          Start from a blank chart. Students will not see the master.
        </EmptyState>
      ) : (
        <Paper sx={{ overflowX: "auto" }}>
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell>Patient</TableCell>
                <TableCell sx={{ display: { xs: "none", sm: "table-cell" } }}>MRN</TableCell>
                <TableCell sx={{ display: { xs: "none", md: "table-cell" } }}>Discipline</TableCell>
                <TableCell sx={{ display: { xs: "none", md: "table-cell" } }}>Updated</TableCell>
                <TableCell />
              </TableRow>
            </TableHead>
            <TableBody>
              {cases.data?.map((item) => (
                <TableRow key={item.id} hover sx={{ cursor: "pointer" }} onClick={() => navigate(`/cases/${item.id}`)}>
                  <TableCell>
                    <Typography variant="body2" sx={{ fontWeight: 700 }}>{item.lastName}, {item.firstName}</Typography>
                    <Typography variant="caption" color="text.secondary">{item.chiefComplaint || "No chief complaint yet"}</Typography>
                  </TableCell>
                  <TableCell sx={{ display: { xs: "none", sm: "table-cell" } }}>{item.mrn}</TableCell>
                  <TableCell sx={{ display: { xs: "none", md: "table-cell" } }}>{item.status.program || "—"}</TableCell>
                  <TableCell sx={{ display: { xs: "none", md: "table-cell" } }}>{formatDateTime(item.updatedAt)}</TableCell>
                  <TableCell align="right" onClick={(e) => e.stopPropagation()}>
                    <Button size="small" onClick={(e) => setRowMenu({ anchor: e.currentTarget, item })}>Actions</Button>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </Paper>
      )}

      <Menu
        anchorEl={rowMenu?.anchor}
        open={Boolean(rowMenu)}
        onClose={() => setRowMenu(undefined)}
      >
        <MenuItem onClick={() => { setCopyTarget(rowMenu?.item); setRowMenu(undefined); }}>Copy to course</MenuItem>
        <MenuItem onClick={() => { setAssignCase(rowMenu?.item); setRowMenu(undefined); }}>Assign</MenuItem>
        <MenuItem onClick={() => { setSimCase(rowMenu?.item); setRowMenu(undefined); }}>Simulate</MenuItem>
      </Menu>

      {copyTarget && (
        <CopyCaseDialog
          item={copyTarget}
          onClose={() => setCopyTarget(undefined)}
          onCopied={(name) => {
            setCopyTarget(undefined);
            setNotice(`${copyTarget.lastName}, ${copyTarget.firstName} copied to ${name}.`);
          }}
        />
      )}

      {simCase && (
        <StartSimulationDialog
          item={simCase}
          onClose={() => setSimCase(undefined)}
          onStarted={() => {
            setNotice(`${simCase.lastName}, ${simCase.firstName} is live for the assigned team. Open it from the Simulation tab.`);
            setSimCase(undefined);
          }}
        />
      )}

      {assignCase && (
        <AssignCaseDialog
          open
          rows={[]}
          initialSourceId={assignCase.id}
          onClose={() => setAssignCase(undefined)}
          onAssigned={() => setAssignCase(undefined)}
        />
      )}
    </Box>
  );
}

function CopyCaseDialog({ item, onClose, onCopied }: { item: AuthoredCase; onClose: () => void; onCopied: (courseName: string) => void }) {
  const { user, activeRole, courseId } = useSession();
  const courses = useAsync(() => listCoursesForUser(), [user.id]);
  const teaching = new Set([
    ...courseIdsForRole(user, "instructor"),
    ...courseIdsForRole(user, "course_coordinator"),
  ]);
  const destinations = (courses.data ?? []).filter((course) => course.id !== courseId && teaching.has(course.id));
  const [destinationId, setDestinationId] = useState(destinations[0]?.id ?? "");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const selected = destinations.find((course) => course.id === destinationId) ?? destinations[0];

  return (
    <Dialog open onClose={onClose} fullWidth maxWidth="xs">
      <DialogTitle>Copy {item.lastName}, {item.firstName}</DialogTitle>
      <DialogContent>
        <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
          Creates a new case in the other course, including the answer key, rubric, and planted triggers. Assigned charts and notes stay here.
        </Typography>
        {destinations.length === 0 ? (
          <Alert severity="info">You teach only this course, so there is nowhere to copy it.</Alert>
        ) : (
          <TextField
            select
            fullWidth
            label="Destination course"
            value={selected?.id ?? ""}
            onChange={(e) => setDestinationId(e.target.value)}
          >
            {destinations.map((course) => (
              <MenuItem key={course.id} value={course.id}>{course.code} · {course.title}</MenuItem>
            ))}
          </TextField>
        )}
        {error && <Alert severity="error" sx={{ mt: 2 }}>{error}</Alert>}
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose}>Cancel</Button>
        <Button
          variant="contained"
          disabled={busy || !selected}
          onClick={async () => {
            if (!selected) return;
            setBusy(true);
            setError("");
            try {
              await copyCase(activeRole, item.id, selected.id);
              onCopied(`${selected.code}`);
            } catch (e) {
              setError((e as Error).message);
              setBusy(false);
            }
          }}
        >Copy</Button>
      </DialogActions>
    </Dialog>
  );
}
