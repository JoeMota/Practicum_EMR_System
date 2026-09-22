import { useState } from "react";
import { Box, Breadcrumbs, Button, LinearProgress, Link, Paper, Stack, Tab, Tabs, Typography } from "@mui/material";
import { Link as RouterLink, useNavigate, useParams, useSearchParams } from "react-router-dom";
import { getPatient, updatePatientStatus } from "../../api/patients";
import { listNotesForPatient } from "../../api/notes";
import { useSession } from "../auth/AuthContext";
import { can } from "../../utils/permissions";
import { useAsync } from "../../utils/useAsync";
import PageError from "../../components/PageError";
import PatientBanner from "./components/PatientBanner";
import StatusDialog from "./components/StatusDialog";
import SummaryTab from "./components/SummaryTab";
import NotesList from "../encounters/components/NotesList";
import MedicationsTab from "../medications/MedicationsTab";
import LabsTab from "../labs/LabsTab";
import SchedulingTab from "../scheduling/SchedulingTab";

const TABS = [
  { id: "summary", label: "Summary" },
  { id: "notes", label: "Notes" },
  { id: "medications", label: "Medications" },
  { id: "labs", label: "Labs" },
  { id: "scheduling", label: "Appointments & referrals" },
] as const;
type TabId = (typeof TABS)[number]["id"];

export default function PatientChartPage() {
  const { patientId = "" } = useParams();
  const navigate = useNavigate();
  const [params, setParams] = useSearchParams();
  const tab = (TABS.find((t) => t.id === params.get("tab"))?.id ?? "summary") as TabId;
  const { user, activeRole } = useSession();
  const [statusOpen, setStatusOpen] = useState(false);

  const patient = useAsync(() => getPatient(user, activeRole, patientId), [patientId, user.id, activeRole]);
  const notes = useAsync(() => listNotesForPatient(user, activeRole, patientId), [patientId, user.id, activeRole]);

  if (patient.error) return <PageError error={patient.error} />;
  if (!patient.data) return <LinearProgress aria-label="Loading chart" />;
  const p = patient.data;

  return (
    <Stack spacing={2}>
      <Breadcrumbs>
        <Link component={RouterLink} to="/patients" underline="hover">Patients</Link>
        <Typography color="text.primary">{p.lastName}, {p.firstName}</Typography>
      </Breadcrumbs>

      <PatientBanner
        patient={p}
        ownerName={p.ownerName}
        onEditStatus={can(activeRole, "patient:update_status") ? () => setStatusOpen(true) : undefined}
      />

      <Paper sx={{ px: 1 }}>
        <Tabs
          value={tab} variant="scrollable" allowScrollButtonsMobile aria-label="Chart sections"
          onChange={(_, v) => setParams({ tab: v }, { replace: true })}
        >
          {TABS.map((t) => (
            <Tab key={t.id} value={t.id} label={t.id === "notes" && notes.data ? `${t.label} (${notes.data.length})` : t.label} />
          ))}
        </Tabs>
      </Paper>

      <Box role="tabpanel" aria-label={TABS.find((t) => t.id === tab)?.label}>
        {tab === "summary" && (
          <SummaryTab
            patient={p}
            notes={notes.data ?? []}
            onAdvance={async (next) => {
              patient.setData(await updatePatientStatus(user, activeRole, p.id, { encounter: next }));
            }}
          />
        )}
        {tab === "notes" && (
          <Paper sx={{ p: 2.5 }}>
            <NotesList
              notes={notes.data ?? []}
              patientId={p.id}
              reviewer={!can(activeRole, "note:author")}
              emptyAction={
                can(activeRole, "note:author") ? (
                  <Button variant="contained" onClick={() => navigate(`/patients/${p.id}/notes/new`)}>
                    Start note
                  </Button>
                ) : undefined
              }
            />
          </Paper>
        )}
        {tab === "medications" && <MedicationsTab patient={p} />}
        {tab === "labs" && <LabsTab patient={p} />}
        {tab === "scheduling" && <SchedulingTab patient={p} />}
      </Box>

      <Typography variant="caption" color="text.secondary">
        Opening this chart was recorded in the activity log.
      </Typography>

      {statusOpen && (
        <StatusDialog
          open patient={p} onClose={() => setStatusOpen(false)}
          onSave={async (status) => patient.setData(await updatePatientStatus(user, activeRole, p.id, status))}
        />
      )}
    </Stack>
  );
}
