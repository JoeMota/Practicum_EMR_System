import { useMemo, useState } from "react";
import {
  Alert, Box, Button, Chip, Dialog, DialogActions, DialogContent, DialogContentText, DialogTitle,
  LinearProgress, Paper, Tab, Table, TableBody, TableCell, TableHead, TableRow, Tabs, Typography,
} from "@mui/material";
import { useNavigate, useSearchParams } from "react-router-dom";
import { listPatients, resetPracticePatient, unassignCase, type PatientRow } from "../../api/patients";
import { useSession } from "../auth/AuthContext";
import { can } from "../../utils/permissions";
import { formatDateTime } from "../../utils/format";
import { useAsync } from "../../utils/useAsync";
import NoteStatusChip from "../../components/NoteStatusChip";
import EmptyState from "../../components/EmptyState";
import { usePageHeading } from "../../components/PageHeading";
import AssignCaseDialog from "./components/AssignCaseDialog";
import type { CaseMode } from "../../types";

export default function PatientListPage() {
  const navigate = useNavigate();
  const { activeRole, courseId } = useSession();
  const isStudent = activeRole === "student";
  usePageHeading(isStudent ? "My Patients" : "Patients");
  const [params, setParams] = useSearchParams();
  const mode: CaseMode = params.get("mode") === "practice" ? "practice" : "assessment";
  const query = params.get("q") ?? "";
  const [resetTarget, setResetTarget] = useState<PatientRow>();
  const [unassignTarget, setUnassignTarget] = useState<PatientRow>();
  const [assignOpen, setAssignOpen] = useState(false);
  const [flash, setFlash] = useState<{ severity: "success" | "error"; text: string }>();

  const rows = useAsync(() => listPatients(activeRole, courseId), [activeRole, courseId]);
  const canAssign = can(activeRole, "patient:create");

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
    try {
      await resetPracticePatient(activeRole, resetTarget.patient.id);
      setFlash({
        severity: "success",
        text: `${resetTarget.patient.practiceLabel} was reset. Students' practice notes were archived.`,
      });
      setResetTarget(undefined);
      rows.reload();
    } catch (e) {
      setResetTarget(undefined);
      setFlash({ severity: "error", text: (e as Error).message || "Couldn't reset that practice patient." });
    }
  };

  const doUnassign = async () => {
    if (!unassignTarget) return;
    try {
      await unassignCase(activeRole, unassignTarget.patient.id);
      setFlash({
        severity: "success",
        text: `${unassignTarget.patient.lastName}, ${unassignTarget.patient.firstName} was removed from ${unassignTarget.ownerName ?? "the student"}.`,
      });
      setUnassignTarget(undefined);
      rows.reload();
    } catch (e) {
      setUnassignTarget(undefined);
      setFlash({ severity: "error", text: (e as Error).message || "Couldn't remove that assignment." });
    }
  };

  return (
    <Box>
      {flash && (
        <Alert severity={flash.severity} onClose={() => setFlash(undefined)} sx={{ mb: 2 }}>{flash.text}</Alert>
      )}
      <Paper>
        <Tabs
          value={mode} onChange={(_, v) => setParams({ mode: v, ...(query ? { q: query } : {}) }, { replace: true })}
          sx={{ px: 1, borderBottom: 1, borderColor: "divider" }} aria-label="Case type"
        >
          <Tab value="assessment" label={`${isStudent ? "Assigned cases" : "Assessment cases"} (${counts.assessment})`} />
          <Tab value="practice" label={`Practice patients (${counts.practice})`} />
        </Tabs>

        <Box sx={{ display: "flex", alignItems: "flex-start", gap: 2, px: 2, pt: 1.5, flexWrap: "wrap" }}>
          <Typography variant="body2" color="text.secondary" sx={{ flex: 1, minWidth: 220 }}>
            {mode === "assessment"
              ? isStudent
                ? "Cases your instructor assigned to you. Each one is your own copy: no one else's notes appear on it."
                : "One private copy per student. Open a case to see that student's work, or remove it from them."
              : "Shared patients for learning the system. Nothing here is graded, and instructors reset them between sessions."}
          </Typography>
          {canAssign && (
            <Button size="small" variant="contained" onClick={() => setAssignOpen(true)}>Assign case</Button>
          )}
        </Box>

        {rows.loading && <LinearProgress sx={{ mt: 1 }} aria-label="Loading patients" />}

        <Box sx={{ overflowX: "auto", p: 1 }}>
          {rows.loading ? null : visible.length === 0 ? (
            <Box sx={{ p: 2 }}>
              <EmptyState
                title={query ? "No patients match that search" : mode === "assessment" ? "No cases assigned yet" : "No practice patients in this course"}
                action={!query && mode === "assessment" && canAssign ? <Button variant="contained" onClick={() => setAssignOpen(true)}>Assign case</Button> : undefined}
              >
                {query ? "Try a last name or the full MRN." : mode === "assessment" && isStudent ? "Your instructor will assign cases here. Try a practice patient in the meantime." : mode === "assessment" && canAssign ? "Pick students and a case to create their private copies." : undefined}
              </EmptyState>
            </Box>
          ) : (
            <Table size="small" sx={{ minWidth: { xs: 0, sm: 640 } }}>
              <TableHead>
                <TableRow>
                  <TableCell>Patient</TableCell>
                  {!isStudent && mode === "assessment" && (
                    <TableCell sx={{ display: { xs: "none", md: "table-cell" } }}>Student</TableCell>
                  )}
                  <TableCell sx={{ display: { xs: "none", sm: "table-cell" } }}>Age, sex</TableCell>
                  <TableCell sx={{ display: { xs: "none", sm: "table-cell" } }}>Visit</TableCell>
                  <TableCell>{isStudent ? "My note" : "Latest note"}</TableCell>
                  <TableCell align="right"><Box component="span" sx={visuallyHidden}>Actions</Box></TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {visible.map((r) => {
                  const p = r.patient;
                  const open = () => navigate(`/patients/${p.id}`);
                  return (
                    <TableRow
                      key={p.id}
                      hover
                      onClick={open}
                      onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); open(); } }}
                      tabIndex={0}
                      sx={{ cursor: "pointer" }}
                      aria-label={`Open chart for ${p.lastName}, ${p.firstName}`}
                    >
                      <TableCell sx={{ maxWidth: { xs: 140, sm: "none" } }}>
                        <Typography variant="body2" sx={{ fontWeight: 700 }}>
                          {p.lastName}, {p.firstName}
                          {p.practiceLabel && <Chip size="small" label={p.practiceLabel} variant="outlined" sx={{ ml: 1 }} />}
                        </Typography>
                        <Typography variant="caption" color="text.secondary">MRN {p.mrn}</Typography>
                        <Typography
                          variant="caption"
                          color="text.secondary"
                          sx={{ display: { xs: "block", sm: "none" } }}
                        >
                          {p.ageYears} y, {p.sexAtBirth} · {p.status.encounter}
                        </Typography>
                      </TableCell>
                      {!isStudent && mode === "assessment" && (
                        <TableCell sx={{ display: { xs: "none", md: "table-cell" } }}>{r.ownerName}</TableCell>
                      )}
                      <TableCell sx={{ display: { xs: "none", sm: "table-cell" } }}>
                        {p.ageYears} y, {p.sexAtBirth}
                      </TableCell>
                      <TableCell sx={{ display: { xs: "none", sm: "table-cell" } }}>
                        <Chip size="small" label={p.status.encounter} color={p.status.encounter === "Checked in" || p.status.encounter === "In progress" ? "info" : "default"} variant="outlined" />
                      </TableCell>
                      <TableCell>
                        <NoteStatusChip status={r.latestNote?.status} />
                        {r.latestNote && (
                          <Typography
                            variant="caption"
                            color="text.secondary"
                            sx={{ display: { xs: "none", sm: "block" } }}
                          >
                            {formatDateTime(r.latestNote.updatedAt)}
                          </Typography>
                        )}
                      </TableCell>
                      <TableCell align="right" sx={{ whiteSpace: "nowrap", pl: { xs: 0.5, sm: 2 } }} onClick={(e) => e.stopPropagation()}>
                        {mode === "practice" && can(activeRole, "patient:reset_practice") && (
                          <Button size="small" color="inherit" onClick={() => setResetTarget(r)} sx={{ mr: 1, display: { xs: "none", sm: "inline-flex" } }}>Reset</Button>
                        )}
                        {mode === "assessment" && canAssign && (
                          <Button size="small" color="inherit" onClick={() => setUnassignTarget(r)} sx={{ mr: 1, display: { xs: "none", sm: "inline-flex" } }}>Remove</Button>
                        )}
                        <Button size="small" variant="contained" onClick={open}>
                          <Box component="span" sx={{ display: { xs: "none", sm: "inline" } }}>Open chart</Box>
                          <Box component="span" sx={{ display: { xs: "inline", sm: "none" } }}>Open</Box>
                        </Button>
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

      <Dialog open={Boolean(unassignTarget)} onClose={() => setUnassignTarget(undefined)}>
        <DialogTitle>Remove this case from {unassignTarget?.ownerName ?? "the student"}?</DialogTitle>
        <DialogContent>
          <DialogContentText>
            {unassignTarget?.patient.lastName}, {unassignTarget?.patient.firstName} will disappear from their patient list. Their notes on this copy are no longer reachable. Other students' copies are unchanged.
          </DialogContentText>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setUnassignTarget(undefined)}>Cancel</Button>
          <Button variant="contained" color="error" onClick={doUnassign}>Remove assignment</Button>
        </DialogActions>
      </Dialog>

      {assignOpen && (
        <AssignCaseDialog
          open
          rows={rows.data ?? []}
          onClose={() => setAssignOpen(false)}
          onAssigned={(assigned) => {
            const names = assigned.map((p) => `${p.lastName}, ${p.firstName}`).join("; ");
            setFlash({
              severity: "success",
              text: `Assigned ${assigned.length === 1 ? "a case" : `${assigned.length} copies`}: ${names}.`,
            });
            setParams({ mode: "assessment" }, { replace: true });
            rows.reload();
          }}
        />
      )}
    </Box>
  );
}

const visuallyHidden = {
  position: "absolute", width: 1, height: 1, overflow: "hidden", clip: "rect(0 0 0 0)", whiteSpace: "nowrap",
} as const;
