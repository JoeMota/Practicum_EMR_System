import { useMemo, useState } from "react";
import {
  Alert, Box, Button, Chip, Dialog, DialogActions, DialogContent, DialogContentText, DialogTitle,
  LinearProgress, Paper, Tab, Table, TableBody, TableCell, TableHead, TableRow, Tabs, Typography,
} from "@mui/material";
import Check from "@mui/icons-material/Check";
import { Link as RouterLink, useNavigate, useSearchParams } from "react-router-dom";
import { listPatients, resetPracticePatient, unassignCase, type PatientRow } from "../../api/patients";
import { useSession } from "../auth/useSession";
import { can } from "../../utils/permissions";
import { formatDate, formatDateTime } from "../../utils/format";
import { useAsync } from "../../utils/useAsync";
import NoteStatusChip from "../../components/NoteStatusChip";
import EmptyState from "../../components/EmptyState";
import { usePageHeading } from "../../components/usePageHeading";
import AssignCaseDialog from "./components/AssignCaseDialog";
import { CASELOAD_VIEWS, caseloadHref, caseloadViewMeta, matchesCaseload, parseCaseloadView } from "./caseload";
import type { CaseMode } from "../../types";
import { phaseChip } from "./simulation";

export default function PatientListPage() {
  const navigate = useNavigate();
  const { activeRole, courseId } = useSession();
  const isStudent = activeRole === "student";
  const [params, setParams] = useSearchParams();
  const requested = params.get("mode");
  const mode: CaseMode = requested === "practice" || requested === "simulation" ? requested : "assessment";
  const query = params.get("q") ?? "";
  const view = isStudent ? parseCaseloadView(params.get("view")) : undefined;
  const viewMeta = view ? caseloadViewMeta(view) : undefined;
  usePageHeading(viewMeta?.label ?? (isStudent ? "My Patients" : "Patients"));
  const [resetTarget, setResetTarget] = useState<PatientRow>();
  const [unassignTarget, setUnassignTarget] = useState<PatientRow>();
  const [assignOpen, setAssignOpen] = useState(false);
  const [flash, setFlash] = useState<{ severity: "success" | "error"; text: string }>();

  const rows = useAsync(() => listPatients(activeRole, courseId), [activeRole, courseId]);
  const canAssign = can(activeRole, "patient:create");

  const clinical = useMemo(
    () => (rows.data ?? []).filter((r) => r.patient.mode !== "case"),
    [rows.data],
  );
  const counts = useMemo(() => ({
    assessment: clinical.filter((r) => r.patient.mode === "assessment").length,
    practice: clinical.filter((r) => r.patient.mode === "practice").length,
    simulation: clinical.filter((r) => r.patient.mode === "simulation").length,
  }), [clinical]);

  const visible = clinical
    .filter((r) => (view ? matchesCaseload(r, view) : r.patient.mode === mode))
    .filter((r) => {
      const q = query.trim().toLowerCase();
      if (!q) return true;
      const p = r.patient;
      const dob = (p.dob || "").slice(0, 10);
      const [year, month, day] = dob.split("-");
      const numericDob = year && month && day ? `${month}/${day}/${year}` : "";
      return [p.firstName, p.lastName, p.mrn, r.ownerName ?? "", dob, numericDob, dob ? formatDate(dob) : ""]
        .some((v) => v.toLowerCase().includes(q));
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
        text: unassignTarget.patient.mode === "simulation"
          ? `${unassignTarget.patient.lastName}, ${unassignTarget.patient.firstName} was ended.`
          : `${unassignTarget.patient.lastName}, ${unassignTarget.patient.firstName} was removed from ${unassignTarget.ownerName ?? "the student"}.`,
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
        {view && viewMeta ? (
          <Box sx={{ px: 2.5, pt: 2.5, pb: 1 }}>
            <Typography sx={{ fontSize: 28, fontWeight: 500, color: "#202124", lineHeight: 1.2 }}>
              Filter by category
            </Typography>
            <Typography sx={{ mt: 0.5, fontSize: 16, color: "#5F6368" }}>{viewMeta.description}</Typography>
            <Box
              role="navigation"
              aria-label="Patient categories"
              sx={{ display: "flex", flexWrap: "wrap", gap: 1.5, mt: 2.5 }}
            >
              {CASELOAD_VIEWS.map((item) => {
                const selected = item.id === view;
                const count = clinical.filter((r) => matchesCaseload(r, item.id)).length;
                return (
                  <Chip
                    key={item.id}
                    component={RouterLink}
                    to={caseloadHref(item.id, query)}
                    clickable
                    variant="outlined"
                    icon={selected ? <Check /> : undefined}
                    label={`${item.label} (${count})`}
                    aria-current={selected ? "page" : undefined}
                    sx={categoryChipSx(selected)}
                  />
                );
              })}
            </Box>
            <Button
              component={RouterLink}
              to={query ? `/patients?q=${encodeURIComponent(query)}` : "/patients"}
              sx={{
                mt: 2.5, alignSelf: "flex-start", bgcolor: "#F1F3F4", color: "#3C4043",
                borderRadius: "10px", px: 2.75, py: 1.25, minHeight: 48, fontSize: 15, fontWeight: 600,
                "&:hover": { bgcolor: "#E8EAED" },
              }}
            >
              All patients
            </Button>
          </Box>
        ) : (
        <Tabs
          value={mode} onChange={(_, v) => setParams({ mode: v, ...(query ? { q: query } : {}) }, { replace: true })}
          sx={{ px: 1, borderBottom: 1, borderColor: "divider" }} aria-label="Case type"
        >
          <Tab value="assessment" label={`${isStudent ? "Assigned cases" : "Assessment cases"} (${counts.assessment})`} />
          <Tab value="practice" label={`Practice patients (${counts.practice})`} />
          <Tab value="simulation" label={`Simulation (${counts.simulation})`} />
        </Tabs>
        )}

        {!view && (
        <Box sx={{ display: "flex", alignItems: "flex-start", gap: 2, px: 2, pt: 1.5, flexWrap: "wrap" }}>
          <Typography variant="body2" color="text.secondary" sx={{ flex: 1, minWidth: 220 }}>
            {mode === "assessment"
              ? "Private copies. Each student's notes stay on their own chart."
              : mode === "simulation"
                ? "Shared chart. Amber until vitals are in, then green for the pharmacist or provider."
                : "Shared patients for practice. Nothing here is graded."}
          </Typography>
          {canAssign && (
            <Button size="small" variant="contained" onClick={() => setAssignOpen(true)}>Assign case</Button>
          )}
        </Box>
        )}

        {rows.loading && <LinearProgress sx={{ mt: 1 }} aria-label="Loading patients" />}

        <Box sx={{ overflowX: "auto", p: 1 }}>
          {rows.loading ? null : visible.length === 0 ? (
            <Box sx={{ p: 2 }}>
              <EmptyState
                title={query ? "No patients match that search" : viewMeta ? viewMeta.emptyTitle : mode === "assessment" ? "No cases assigned yet" : mode === "simulation" ? "No simulations yet" : "No practice patients in this course"}
                action={!query && !view && mode === "assessment" && canAssign ? <Button variant="contained" onClick={() => setAssignOpen(true)}>Assign case</Button> : undefined}
              >
                {query ? "Try a last name, a date of birth, or the full MRN." : viewMeta ? viewMeta.emptyBody : mode === "assessment" && isStudent ? "Your instructor will assign cases here. Try a practice patient in the meantime." : mode === "assessment" && canAssign ? "Pick students and a case to create their private copies." : mode === "practice" ? "Practice patients are shared copies for learning the screens. They are not graded." : mode === "simulation" ? "Start one from a case. Only the assigned nurse, pharmacist, and provider can open it." : undefined}
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
                      sx={{
                        cursor: "pointer",
                        boxShadow: mode === "simulation" ? `inset 4px 0 0 ${phaseChip(p.simulationPhase).color}` : undefined,
                        bgcolor: mode === "simulation" ? phaseChip(p.simulationPhase).bgcolor : undefined,
                      }}
                      aria-label={`Open chart for ${p.lastName}, ${p.firstName}`}
                    >
                      <TableCell sx={{ maxWidth: { xs: 140, sm: "none" } }}>
                        <Typography variant="body2" sx={{ fontWeight: 700 }}>
                          {p.lastName}, {p.firstName}
                        </Typography>
                        <Typography variant="caption" color="text.secondary" sx={{ display: "block", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis", maxWidth: { xs: 140, sm: 280 } }}>
                          {p.practiceLabel ? `${p.practiceLabel} · ` : ""}
                          {mode === "simulation" ? `${phaseChip(p.simulationPhase).label} · ` : ""}
                          MRN {p.mrn}
                        </Typography>
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
                        {p.status.encounter}
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
                        {mode === "simulation" && canAssign && (
                          <Button size="small" color="inherit" onClick={() => setUnassignTarget(r)} sx={{ mr: 1, display: { xs: "none", sm: "inline-flex" } }}>End</Button>
                        )}
                        <Button size="small" onClick={open}>
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
        <DialogTitle>
          {unassignTarget?.patient.mode === "simulation"
            ? "End this simulation?"
            : `Remove this case from ${unassignTarget?.ownerName ?? "the student"}?`}
        </DialogTitle>
        <DialogContent>
          <DialogContentText>
            {unassignTarget?.patient.mode === "simulation"
              ? `${unassignTarget.patient.lastName}, ${unassignTarget.patient.firstName} leaves the Simulation tab for everyone assigned to it. Graded charts are not affected.`
              : `${unassignTarget?.patient.lastName}, ${unassignTarget?.patient.firstName} will disappear from their patient list. Their notes on this copy are no longer reachable. Other students' copies are unchanged.`}
          </DialogContentText>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setUnassignTarget(undefined)}>Cancel</Button>
          <Button variant="contained" color="error" onClick={doUnassign}>
            {unassignTarget?.patient.mode === "simulation" ? "End simulation" : "Remove assignment"}
          </Button>
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

const CATEGORY_BLUE = "#1A73E8";

function categoryChipSx(selected: boolean) {
  return {
    height: 42,
    borderRadius: "999px",
    px: 0.25,
    fontSize: 15,
    fontWeight: 600,
    textDecoration: "none",
    bgcolor: "#fff",
    color: selected ? CATEGORY_BLUE : "#3C4043",
    borderColor: selected ? CATEGORY_BLUE : "#DADCE0",
    "& .MuiChip-icon": { color: CATEGORY_BLUE, fontSize: 20, ml: "12px" },
    "& .MuiChip-label": { px: 1.75 },
    "&:hover, &.MuiChip-clickable:hover": {
      bgcolor: selected ? "rgba(26,115,232,0.06)" : "#F8F9FA",
    },
  } as const;
}

const visuallyHidden = {
  position: "absolute", width: 1, height: 1, overflow: "hidden", clip: "rect(0 0 0 0)", whiteSpace: "nowrap",
} as const;
