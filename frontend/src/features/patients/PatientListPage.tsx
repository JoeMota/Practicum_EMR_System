import { useMemo, useState } from "react";
import {
  Alert, Box, Button, Chip, Dialog, DialogActions, DialogContent, DialogContentText, DialogTitle,
  InputAdornment, LinearProgress, Paper, Tab, Table, TableBody, TableCell, TableHead, TableRow, Tabs, TextField, Typography,
} from "@mui/material";
import SearchRounded from "@mui/icons-material/SearchRounded";
import { useNavigate, useSearchParams } from "react-router-dom";
import { listPatients, resetPracticePatient, type PatientRow } from "../../api/patients";
import { getCourse } from "../../api/courses";
import { useSession } from "../auth/AuthContext";
import { can } from "../../utils/permissions";
import { formatDateTime } from "../../utils/format";
import { useAsync } from "../../utils/useAsync";
import NoteStatusChip from "../../components/NoteStatusChip";
import EmptyState from "../../components/EmptyState";
import type { CaseMode } from "../../types";

export default function PatientListPage() {
  const navigate = useNavigate();
  const { user, activeRole, courseId } = useSession();
  const [params, setParams] = useSearchParams();
  const mode: CaseMode = params.get("mode") === "practice" ? "practice" : "assessment";
  const [query, setQuery] = useState("");
  const [resetTarget, setResetTarget] = useState<PatientRow>();
  const [flash, setFlash] = useState("");

  const isStudent = activeRole === "student";
  const rows = useAsync(() => listPatients(user, activeRole, courseId), [user.id, activeRole, courseId]);
  const course = useAsync(() => getCourse(courseId), [courseId]);

  const counts = useMemo(() => ({
    assessment: rows.data?.filter((r) => r.patient.mode === "assessment").length ?? 0,
    practice: rows.data?.filter((r) => r.patient.mode === "practice").length ?? 0,
  }), [rows.data]);

  const visible = (rows.data ?? [])
    .filter((r) => r.patient.mode === mode)
    .filter((r) => {
      const q = query.trim().toLowerCase();
      if (!q) return true;
      const p = r.patient;
      return [p.firstName, p.lastName, p.mrn, r.ownerName ?? ""].some((v) => v.toLowerCase().includes(q));
    });

  const doReset = async () => {
    if (!resetTarget) return;
    await resetPracticePatient(user, activeRole, resetTarget.patient.id);
    setFlash(`${resetTarget.patient.practiceLabel} was reset. Students' practice notes were archived.`);
    setResetTarget(undefined);
    rows.reload();
  };

  return (
    <Box>
      <Box sx={{ display: "flex", alignItems: "flex-end", gap: 2, flexWrap: "wrap", mb: 2 }}>
        <Box sx={{ flex: 1, minWidth: 220 }}>
          <Typography component="h1" variant="h5">{isStudent ? "My patients" : "Patients"}</Typography>
          <Typography variant="body2" color="text.secondary">
            {course.data ? `${course.data.code}: ${course.data.title}` : " "}
          </Typography>
        </Box>
        <TextField
          size="small" placeholder={isStudent ? "Search name or MRN" : "Search patient, MRN, or student"}
          value={query} onChange={(e) => setQuery(e.target.value)} sx={{ width: { xs: "100%", sm: 320 } }}
          slotProps={{
            htmlInput: { "aria-label": "Search patients" },
            input: { startAdornment: <InputAdornment position="start"><SearchRounded fontSize="small" /></InputAdornment> },
          }}
        />
      </Box>

      {flash && <Alert severity="success" onClose={() => setFlash("")} sx={{ mb: 2 }}>{flash}</Alert>}
      {rows.error && <Alert severity="error" sx={{ mb: 2 }}>{rows.error.message}</Alert>}

      <Paper>
        <Tabs
          value={mode} onChange={(_, v) => setParams({ mode: v }, { replace: true })}
          sx={{ px: 1, borderBottom: 1, borderColor: "divider" }} aria-label="Case type"
        >
          <Tab value="assessment" label={`${isStudent ? "Assigned cases" : "Assessment cases"} (${counts.assessment})`} />
          <Tab value="practice" label={`Practice patients (${counts.practice})`} />
        </Tabs>

        <Typography variant="body2" color="text.secondary" sx={{ px: 2, pt: 1.5 }}>
          {mode === "assessment"
            ? isStudent
              ? "Cases your instructor assigned to you. Each one is your own copy: no one else's notes appear on it."
              : "One private copy per student. Open a case to see that student's work."
            : "Shared patients for learning the system. Nothing here is graded, and instructors reset them between sessions."}
        </Typography>

        {rows.loading && <LinearProgress sx={{ mt: 1 }} />}

        <Box sx={{ overflowX: "auto", p: 1 }}>
          {!rows.loading && visible.length === 0 ? (
            <Box sx={{ p: 2 }}>
              <EmptyState title={query ? "No patients match that search" : mode === "assessment" ? "No cases assigned yet" : "No practice patients in this course"}>
                {query ? "Try a last name or the full MRN." : mode === "assessment" && isStudent ? "Your instructor will assign cases here. Try a practice patient in the meantime." : undefined}
              </EmptyState>
            </Box>
          ) : (
            <Table>
              <TableHead>
                <TableRow>
                  <TableCell>Patient</TableCell>
                  {!isStudent && mode === "assessment" && <TableCell>Student</TableCell>}
                  <TableCell>Age, sex</TableCell>
                  <TableCell>Visit</TableCell>
                  <TableCell>{isStudent ? "My note" : "Latest note"}</TableCell>
                  <TableCell align="right"><Box component="span" sx={visuallyHidden}>Actions</Box></TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {visible.map((r) => {
                  const p = r.patient;
                  return (
                    <TableRow key={p.id} hover>
                      <TableCell>
                        <Typography variant="body2" sx={{ fontWeight: 700 }}>
                          {p.lastName}, {p.firstName}
                          {p.practiceLabel && <Chip size="small" label={p.practiceLabel} variant="outlined" sx={{ ml: 1 }} />}
                        </Typography>
                        <Typography variant="caption" color="text.secondary">MRN {p.mrn}</Typography>
                      </TableCell>
                      {!isStudent && mode === "assessment" && <TableCell>{r.ownerName}</TableCell>}
                      <TableCell>{p.ageYears} y, {p.sexAtBirth}</TableCell>
                      <TableCell>
                        <Chip size="small" label={p.status.encounter} color={p.status.encounter === "Checked in" || p.status.encounter === "In progress" ? "info" : "default"} variant="outlined" />
                      </TableCell>
                      <TableCell>
                        <NoteStatusChip status={r.latestNote?.status} />
                        {r.latestNote && (
                          <Typography variant="caption" color="text.secondary" sx={{ display: "block" }}>{formatDateTime(r.latestNote.updatedAt)}</Typography>
                        )}
                      </TableCell>
                      <TableCell align="right" sx={{ whiteSpace: "nowrap" }}>
                        {mode === "practice" && can(activeRole, "patient:reset_practice") && (
                          <Button size="small" color="inherit" onClick={() => setResetTarget(r)} sx={{ mr: 1 }}>Reset</Button>
                        )}
                        <Button size="small" variant="outlined" onClick={() => navigate(`/patients/${p.id}`)}>Open chart</Button>
                      </TableCell>
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
          )}
        </Box>
      </Paper>

      <Typography variant="caption" color="text.secondary" sx={{ display: "block", mt: 1.5 }}>
        Every record is simulated and excluded from reporting.
      </Typography>

      <Dialog open={Boolean(resetTarget)} onClose={() => setResetTarget(undefined)}>
        <DialogTitle>Reset {resetTarget?.patient.practiceLabel}?</DialogTitle>
        <DialogContent>
          <DialogContentText>
            The chart goes back to its original state for the next group. Practice notes students wrote on this patient are archived, not deleted.
          </DialogContentText>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setResetTarget(undefined)}>Cancel</Button>
          <Button variant="contained" onClick={doReset}>Reset patient</Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}

const visuallyHidden = {
  position: "absolute", width: 1, height: 1, overflow: "hidden", clip: "rect(0 0 0 0)", whiteSpace: "nowrap",
} as const;
