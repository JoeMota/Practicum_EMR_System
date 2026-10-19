import { useState } from "react";
import { Box, Breadcrumbs, Button, LinearProgress, Link, Paper, Typography } from "@mui/material";
import { Link as RouterLink, useNavigate, useParams, useSearchParams } from "react-router-dom";
import { getPatient, updatePatientStatus } from "../../api/patients";
import { listNotesForPatient } from "../../api/notes";
import { useSession } from "../auth/AuthContext";
import { can } from "../../utils/permissions";
import { useAsync } from "../../utils/useAsync";
import { utep } from "../../theme/tokens";
import PageError from "../../components/PageError";
import { usePageHeading } from "../../components/PageHeading";
import PatientBanner from "./components/PatientBanner";
import StatusDialog from "./components/StatusDialog";
import SummaryTab from "./components/SummaryTab";
import NotesList from "../encounters/components/NotesList";
import MedicationsTab from "../medications/MedicationsTab";
import LabsTab from "../labs/LabsTab";
import SchedulingTab from "../scheduling/SchedulingTab";

const TABS = [
  { id: "summary", label: "Overview" },
  { id: "notes", label: "Notes" },
  { id: "medications", label: "Medications" },
  { id: "labs", label: "Labs" },
  { id: "scheduling", label: "Appointments & Referrals" },
] as const;
type TabId = (typeof TABS)[number]["id"];

export default function PatientChartPage() {
  const { patientId = "" } = useParams();
  const navigate = useNavigate();
  const [params, setParams] = useSearchParams();
  const tab = (TABS.find((t) => t.id === params.get("tab"))?.id ?? "summary") as TabId;
  const { user, activeRole } = useSession();
  const [statusOpen, setStatusOpen] = useState(false);

  const patient = useAsync(() => getPatient(activeRole, patientId), [patientId, activeRole]);
  const notes = useAsync(() => listNotesForPatient(activeRole, patientId), [patientId, activeRole]);
  const heading = patient.data
    ? `${patient.data.lastName}, ${patient.data.firstName}`
    : "Patient chart";
  usePageHeading(heading);

  if (patient.error) return <PageError error={patient.error} />;
  if (!patient.data) return <LinearProgress aria-label="Loading chart" />;
  const p = patient.data;
  const isAuthor = can(activeRole, "note:author");
  const mine = (notes.data ?? []).filter((n) => n.authorId === user.id);
  const openNote = mine.find((n) => n.status === "draft" || n.status === "returned");
  const noteAction = !isAuthor ? undefined : (
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

      <Box
        role="tablist"
        aria-label="Chart sections"
        sx={{ display: "flex", gap: 0.75, flexWrap: "wrap", my: 2 }}
      >
        {TABS.map((t) => {
          const selected = tab === t.id;
          const label = t.id === "notes" && notes.data ? `${t.label} (${notes.data.length})` : t.label;
          return (
            <Box
              key={t.id}
              component="button"
              type="button"
              role="tab"
              aria-selected={selected}
              onClick={() => setParams({ tab: t.id }, { replace: true })}
              sx={{
                border: "none",
                cursor: "pointer",
                px: 1.75,
                py: 1,
                borderRadius: "999px",
                fontWeight: 700,
                fontSize: 14,
                fontFamily: "inherit",
                bgcolor: selected ? utep.navy : "#fff",
                color: selected ? "#fff" : utep.navy,
                boxShadow: selected ? "none" : `inset 0 0 0 1px ${utep.line}`,
                "&:focus-visible": { outline: `3px solid ${utep.orange}`, outlineOffset: 2 },
              }}
            >
              {label}
            </Box>
          );
        })}
      </Box>

      <Box role="tabpanel" aria-label={TABS.find((t) => t.id === tab)?.label}>
        {tab === "summary" && (
          <SummaryTab
            patient={p}
            notes={notes.data ?? []}
            onAdvance={async (next) => {
              patient.setData(await updatePatientStatus(activeRole, p.id, { encounter: next }));
            }}
          />
        )}
        {tab === "notes" && (
          <Paper sx={{ p: 2.5, borderRadius: "16px" }}>
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
          </Paper>
        )}
        {tab === "medications" && <MedicationsTab patient={p} />}
        {tab === "labs" && <LabsTab patient={p} />}
        {tab === "scheduling" && <SchedulingTab patient={p} />}
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
    </Box>
  );
}
