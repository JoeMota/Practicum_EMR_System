import { useState } from "react";
import { Box, LinearProgress, Table, TableBody, TableCell, TableHead, TableRow } from "@mui/material";
import AssignmentOutlined from "@mui/icons-material/AssignmentOutlined";
import PeopleAltOutlined from "@mui/icons-material/PeopleAltOutlined";
import ReplayOutlined from "@mui/icons-material/ReplayOutlined";
import ScienceOutlined from "@mui/icons-material/ScienceOutlined";
import { Link as RouterLink } from "react-router-dom";
import { listPatients, type PatientRow } from "../../api/patients";
import { caseloadHref, matchesCaseload } from "../patients/caseload";
import { useSession } from "../auth/useSession";
import { useAsync } from "../../utils/useAsync";
import EmptyState from "../../components/EmptyState";
import NoteStatusChip from "../../components/NoteStatusChip";
import { Panel, StatCard, StatGrid } from "./components/DashboardParts";
import { DAY_MS, patientName, since } from "./dashboardFormat";
import { utep } from "../../theme/tokens";

function continueTo(row: PatientRow) {
  return `/patients/${row.patient.id}`;
}

export default function StudentDashboard() {
  const { activeRole, courseId } = useSession();
  const patients = useAsync(() => listPatients(activeRole, courseId), [activeRole, courseId]);
  const [now] = useState(() => Date.now());

  if (patients.loading && !patients.data) return <LinearProgress />;

  const rows = patients.data ?? [];
  const assessment = rows.filter((r) => matchesCaseload(r, "assigned"));
  const practice = rows.filter((r) => matchesCaseload(r, "practice"));
  const inProgress = rows.filter((r) => matchesCaseload(r, "in-clinic"));
  const returned = rows.filter((r) => matchesCaseload(r, "returned"));
  const pending = rows.filter((r) => matchesCaseload(r, "awaiting"));
  const flagged = rows.filter((r) => r.patient.labs.some((l) => l.flag));
  const doseFlags = rows.filter((r) => (r.openFlagCount ?? 0) > 0);
  const recentNotes = [...rows]
    .filter((r) => r.latestNote)
    .sort((a, b) => new Date(b.latestNote!.updatedAt).getTime() - new Date(a.latestNote!.updatedAt).getTime())
    .slice(0, 6);
  const stale = assessment.filter((r) => {
    const note = r.latestNote;
    if (!note || note.status === "cosigned") return false;
    return now - new Date(note.updatedAt).getTime() >= DAY_MS;
  });

  return (
    <Box sx={{ display: "grid", gap: 2.5 }}>
      <StatGrid title="Your caseload">
        <StatCard
          label="Assigned patients"
          value={assessment.length}
          tone="navy"
          to={caseloadHref("assigned")}
          icon={<PeopleAltOutlined fontSize="small" />}
        />
        <StatCard
          label="In clinic now"
          value={inProgress.length}
          tone="orange"
          to={caseloadHref("in-clinic")}
          icon={<PeopleAltOutlined fontSize="small" />}
        />
        <StatCard
          label="Returned notes"
          value={returned.length}
          tone="orangeSoft"
          to={caseloadHref("returned")}
          icon={<ReplayOutlined fontSize="small" />}
        />
        <StatCard
          label="Needs review"
          value={pending.length}
          tone="navySoft"
          to={caseloadHref("awaiting")}
          icon={<AssignmentOutlined fontSize="small" />}
        />
        <StatCard
          label="Items to check"
          value={doseFlags.length}
          tone="orange"
          to={caseloadHref("flags")}
          icon={<AssignmentOutlined fontSize="small" />}
        />
        <StatCard
          label="Practice cases"
          value={practice.length}
          tone="navy"
          to={caseloadHref("practice")}
          icon={<ScienceOutlined fontSize="small" />}
        />
      </StatGrid>

      <Box sx={{ display: "grid", gap: 2.5, gridTemplateColumns: { xs: "1fr", lg: "1.45fr 1fr" } }}>
        <Panel title="Continue where you left off" accent>
          {stale.length === 0 && assessment.length === 0 ? (
            <EmptyState title="No assigned patients yet">Your instructor will add assessment cases here.</EmptyState>
          ) : (
            <Table size="small" aria-label="Patients to continue">
              <TableHead>
                <TableRow>
                  <TableCell>Patient</TableCell>
                  <TableCell>Visit</TableCell>
                  <TableCell>Note</TableCell>
                  <TableCell>Updated</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {(stale.length ? stale : assessment).slice(0, 8).map((r) => (
                  <TableRow
                    key={r.patient.id}
                    hover
                    component={RouterLink}
                    to={continueTo(r)}
                    sx={{ textDecoration: "none", "&:hover td": { color: utep.navy } }}
                  >
                    <TableCell sx={{ fontWeight: 600 }}>{patientName(r.patient)}</TableCell>
                    <TableCell>{r.patient.status.encounter}</TableCell>
                    <TableCell><NoteStatusChip status={r.latestNote?.status} /></TableCell>
                    <TableCell>{r.latestNote ? since(r.latestNote.updatedAt, now) : "—"}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </Panel>

        <Panel title="Recent notes" action={{ label: "All patients", to: "/patients" }}>
          {recentNotes.length === 0 ? (
            <EmptyState title="No notes yet">Open a chart to start a note.</EmptyState>
          ) : (
            <Table size="small" aria-label="Recent notes">
              <TableHead>
                <TableRow>
                  <TableCell>Patient</TableCell>
                  <TableCell>Status</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {recentNotes.map((r) => (
                  <TableRow
                    key={r.patient.id}
                    hover
                    component={RouterLink}
                    to={continueTo(r)}
                    sx={{ textDecoration: "none" }}
                  >
                    <TableCell sx={{ fontWeight: 600 }}>{patientName(r.patient)}</TableCell>
                    <TableCell><NoteStatusChip status={r.latestNote?.status} /></TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </Panel>
      </Box>

      {flagged.length > 0 && (
        <Panel title="Charts with flagged labs">
          <Table size="small" aria-label="Flagged labs">
            <TableHead>
              <TableRow>
                <TableCell>Patient</TableCell>
                <TableCell>Finding</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {flagged.slice(0, 6).map((r) => {
                const lab = r.patient.labs.find((l) => l.flag);
                return (
                  <TableRow
                    key={r.patient.id}
                    hover
                    component={RouterLink}
                    to={`/patients/${r.patient.id}`}
                    sx={{ textDecoration: "none" }}
                  >
                    <TableCell sx={{ fontWeight: 600 }}>{patientName(r.patient)}</TableCell>
                    <TableCell>{lab ? `${lab.name} ${lab.value} ${lab.unit} (${lab.flag})` : "—"}</TableCell>
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>
        </Panel>
      )}
    </Box>
  );
}
