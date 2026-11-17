import { useEffect, useState } from "react";
import { Alert, Box, Breadcrumbs, Button, Dialog, DialogActions, DialogContent, DialogTitle, LinearProgress, Link, Tab, Tabs, TextField, Typography } from "@mui/material";
import { Link as RouterLink, useNavigate, useParams, useSearchParams } from "react-router-dom";
import { getPatient, updatePatientStatus } from "../../api/patients";
import { grantPortalAccess } from "../../api/users";
import { recordPresence, updatePlacement } from "../../api/chart";
import { listNotesForPatient } from "../../api/notes";
import { useSession } from "../auth/useSession";
import { can } from "../../utils/permissions";
import { useAsync } from "../../utils/useAsync";
import { utep } from "../../theme/tokens";
import PageError from "../../components/PageError";
import { usePageHeading } from "../../components/usePageHeading";
import PatientBanner from "./components/PatientBanner";
import StatusDialog from "./components/StatusDialog";
import SummaryTab from "./components/SummaryTab";
import NotesList from "../encounters/components/NotesList";
import MedicationsTab from "../medications/MedicationsTab";
import LabsTab from "../labs/LabsTab";
import SchedulingTab from "../scheduling/SchedulingTab";
import { simulationNoteAction } from "./simulation";

const TABS = [
  { id: "summary", label: "Overview" },
  { id: "labs", label: "Labs" },
  { id: "medications", label: "Medications" },
  { id: "notes", label: "Notes" },
  { id: "appointments", label: "Appointments" },
  { id: "referrals", label: "Referrals" },
] as const;
type TabId = (typeof TABS)[number]["id"];

export default function PatientChartPage() {
  const { patientId = "" } = useParams();
  const navigate = useNavigate();
  const [params, setParams] = useSearchParams();
  const tab = (TABS.find((t) => t.id === params.get("tab"))?.id ?? "summary") as TabId;
  const { user, activeRole } = useSession();
  const [statusOpen, setStatusOpen] = useState(false);
  const [placement, setPlacement] = useState({ unit: "", room: "", bed: "" });
  const [portalAccessOpen, setPortalAccessOpen] = useState(false);
  const [portalEmail, setPortalEmail] = useState("");
  const [portalFullName, setPortalFullName] = useState("");
  const [portalBusy, setPortalBusy] = useState(false);
  const [portalError, setPortalError] = useState("");
  const [portalGranted, setPortalGranted] = useState(false);
  const [temporaryPassword, setTemporaryPassword] = useState("");

  const patient = useAsync(() => getPatient(activeRole, patientId), [patientId, activeRole]);
  const notes = useAsync(() => listNotesForPatient(activeRole, patientId), [patientId, activeRole]);
  const heading = patient.data
    ? `${patient.data.lastName}, ${patient.data.firstName}`
    : "Patient chart";
  usePageHeading(heading);
  const chartId = patient.data?.id;

  useEffect(() => {
    if (!chartId) return;
    let lastInput = Date.now();
    const mark = () => { lastInput = Date.now(); };
    window.addEventListener("pointerdown", mark);
    window.addEventListener("pointermove", mark);
    window.addEventListener("keydown", mark);
    const beat = () => {
      const active = document.visibilityState === "visible" && Date.now() - lastInput < 60_000;
      if (!active) return;
      recordPresence(activeRole, patientId).catch(() => undefined);
    };
    beat();
    const timer = window.setInterval(beat, 25_000);
    return () => {
      window.clearInterval(timer);
      window.removeEventListener("pointerdown", mark);
      window.removeEventListener("pointermove", mark);
      window.removeEventListener("keydown", mark);
    };
  }, [chartId, patientId, activeRole]);

  if (patient.error) return <PageError error={patient.error} />;
  if (!patient.data) return <LinearProgress aria-label="Loading chart" />;
  const p = patient.data;
  const isAuthor = can(activeRole, "note:author");
  const mine = (notes.data ?? []).filter((n) => n.authorId === user.id);
  const openNote = mine.find((n) => n.status === "draft" || n.status === "returned");
  const simAction = p.mode === "simulation" ? simulationNoteAction(p, notes.data ?? [], user.id) : undefined;
  const noteAction = simAction !== undefined ? (simAction ? (
    <Button variant="contained" color="secondary" onClick={() => navigate(simAction.href)}>{simAction.label}</Button>
  ) : undefined) : !isAuthor ? undefined : (
    <Button
      variant="contained"
      color="secondary"
      onClick={() => navigate(openNote ? `/patients/${p.id}/notes/${openNote.id}` : `/patients/${p.id}/notes/new`)}
    >
      {openNote ? (openNote.status === "returned" ? "Revise returned note" : "Continue note") : "Start note"}
    </Button>
  );

  return (
    <Box>
      <Breadcrumbs aria-label="Breadcrumb" sx={{ mb: 2 }}>
        <Link component={RouterLink} to="/patients" underline="hover">
          {activeRole === "student" ? "My patients" : "Patients"}
        </Link>
        <Typography color="text.primary">{p.lastName}, {p.firstName}</Typography>
      </Breadcrumbs>

      <PatientBanner
        patient={p}
        ownerName={p.ownerName}
        onEditStatus={can(activeRole, "patient:update_status") ? () => setStatusOpen(true) : undefined}
      />

      {(can(activeRole, "user:manage_access") || can(activeRole, "patient:update_status")) && (
        <Box sx={{ px: 0, py: 1.5, my: 1.5, display: "flex", gap: 1.25, flexWrap: "wrap", alignItems: "center", borderBottom: `1px solid ${utep.lineSoft}` }}>
          {can(activeRole, "patient:update_status") && (
            <>
              <Typography variant="body2" sx={{ fontWeight: 700, color: utep.navy }}>Placement</Typography>
              <TextField size="small" label="Unit" placeholder={p.unit || "Unit"} value={placement.unit} onChange={(e) => setPlacement({ ...placement, unit: e.target.value })} sx={{ width: 120 }} />
              <TextField size="small" label="Room" placeholder={p.room || "Room"} value={placement.room} onChange={(e) => setPlacement({ ...placement, room: e.target.value })} sx={{ width: 110 }} />
              <TextField size="small" label="Bed" placeholder={p.bed || "Bed"} value={placement.bed} onChange={(e) => setPlacement({ ...placement, bed: e.target.value })} sx={{ width: 100 }} />
              <Button size="small" onClick={async () => patient.setData(await updatePlacement(activeRole, p.id, placement))}>Save</Button>
            </>
          )}
          {can(activeRole, "user:manage_access") && (
            <Button size="small" sx={{ ml: { sm: "auto" } }} onClick={() => {
              setPortalEmail("");
              setPortalFullName(`${p.firstName} ${p.lastName}`);
              setPortalError("");
              setPortalGranted(false);
              setTemporaryPassword("");
              setPortalAccessOpen(true);
            }}>
              Portal access
            </Button>
          )}
        </Box>
      )}

      <Tabs
        value={tab}
        onChange={(_, next: TabId) => setParams({ tab: next }, { replace: true })}
        variant="scrollable"
        scrollButtons="auto"
        aria-label="Chart sections"
        sx={{
          mb: 2,
          minHeight: 44,
          borderBottom: `1px solid ${utep.lineSoft}`,
          "& .MuiTab-root": { minHeight: 44, px: 1.75 },
        }}
      >
        {TABS.map((t) => (
          <Tab
            key={t.id}
            value={t.id}
            label={t.id === "notes" && notes.data ? `${t.label} (${notes.data.length})` : t.label}
          />
        ))}
      </Tabs>

      <Box role="tabpanel" aria-label={TABS.find((t) => t.id === tab)?.label}>
        {tab === "summary" && (
          <SummaryTab
            patient={p}
            notes={notes.data ?? []}
            onChange={patient.setData}
            onAdvance={async (next) => {
              patient.setData(await updatePatientStatus(activeRole, p.id, { encounter: next }));
            }}
          />
        )}
        {tab === "notes" && (
          <Box sx={{ py: 0.5 }}>
            {notes.loading ? (
              <LinearProgress aria-label="Loading notes" />
            ) : (
              <NotesList
                notes={notes.data ?? []}
                patientId={p.id}
                reviewer={!isAuthor}
                emptyAction={noteAction}
              />
            )}
          </Box>
        )}
        {tab === "medications" && <MedicationsTab patient={p} onChange={patient.setData} />}
        {tab === "labs" && <LabsTab patient={p} onChange={patient.setData} />}
        {tab === "appointments" && <SchedulingTab patient={p} section="appointments" />}
        {tab === "referrals" && <SchedulingTab patient={p} section="referrals" />}
      </Box>

      <Typography variant="caption" color="text.secondary" sx={{ display: "block", mt: 2 }}>
        Opening this chart was recorded in the activity log.
      </Typography>

      {statusOpen && (
        <StatusDialog
          open patient={p} onClose={() => setStatusOpen(false)}
          onSave={async (status) => patient.setData(await updatePatientStatus(activeRole, p.id, status))}
        />
      )}

      <Dialog open={portalAccessOpen} onClose={() => !portalBusy && setPortalAccessOpen(false)} fullWidth maxWidth="xs">
        <DialogTitle>Grant portal access</DialogTitle>
        <DialogContent>
          {portalError && <Alert severity="error" sx={{ mb: 2 }}>{portalError}</Alert>}
          {portalGranted ? (
            temporaryPassword ? (
              <Alert severity="success">
                Portal access granted. Copy this temporary password now: <strong>{temporaryPassword}</strong>
              </Alert>
            ) : (
              <Alert severity="success">Portal access granted. The existing account was linked; no temporary password was generated.</Alert>
            )
          ) : (
            <Box sx={{ display: "grid", gap: 2, pt: 1 }}>
              <TextField
                label="Email" type="email" required autoFocus fullWidth
                value={portalEmail} onChange={(event) => setPortalEmail(event.target.value)}
              />
              <TextField
                label="Full name" required fullWidth
                value={portalFullName} onChange={(event) => setPortalFullName(event.target.value)}
              />
            </Box>
          )}
        </DialogContent>
        <DialogActions>
          {portalGranted ? (
            <Button onClick={() => setPortalAccessOpen(false)}>Close</Button>
          ) : (
            <>
              <Button onClick={() => setPortalAccessOpen(false)} disabled={portalBusy}>Cancel</Button>
              <Button
                variant="contained"
                disabled={portalBusy || !portalEmail.trim() || !portalFullName.trim()}
                onClick={async () => {
                  setPortalBusy(true);
                  setPortalError("");
                  try {
                    const result = await grantPortalAccess({
                      email: portalEmail.trim(),
                      fullName: portalFullName.trim(),
                      patientId: p.id,
                    });
                    setTemporaryPassword(result.temporaryPassword ?? "");
                    setPortalGranted(true);
                  } catch (error) {
                    setPortalError((error as Error).message);
                  } finally {
                    setPortalBusy(false);
                  }
                }}
              >
                {portalBusy ? "Granting…" : "Grant access"}
              </Button>
            </>
          )}
        </DialogActions>
      </Dialog>
    </Box>
  );
}
