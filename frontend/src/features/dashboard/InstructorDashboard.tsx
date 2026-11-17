import { useState } from "react";
import { Box, LinearProgress, Table, TableBody, TableCell, TableHead, TableRow, Typography } from "@mui/material";
import AssignmentOutlined from "@mui/icons-material/AssignmentOutlined";
import PeopleAltOutlined from "@mui/icons-material/PeopleAltOutlined";
import ReplayOutlined from "@mui/icons-material/ReplayOutlined";
import ScienceOutlined from "@mui/icons-material/ScienceOutlined";
import { Link as RouterLink } from "react-router-dom";
import { listPatients } from "../../api/patients";
import { listReviewQueue } from "../../api/notes";
import { listAudit } from "../../api/audit";
import { getAtRisk } from "../../api/courses";
import { useSession } from "../auth/useSession";
import { useAsync } from "../../utils/useAsync";
import { formatRelativeShort } from "../../utils/format";
import EmptyState from "../../components/EmptyState";
import { Panel, StatCard, StatGrid } from "./components/DashboardParts";
import { DAY_MS, patientName, since } from "./dashboardFormat";
import { utep } from "../../theme/tokens";
import { actionLabel } from "../admin/auditLabels";

export default function InstructorDashboard() {
  const { activeRole, courseId } = useSession();
  const patients = useAsync(() => listPatients(activeRole, courseId), [activeRole, courseId]);
  const queue = useAsync(() => listReviewQueue(courseId, activeRole), [courseId, activeRole]);
  const audit = useAsync(() => listAudit(courseId, activeRole), [courseId, activeRole]);
  const risk = useAsync(() => getAtRisk(courseId, activeRole), [courseId, activeRole]);
  const [now] = useState(() => Date.now());

  if (patients.loading && !patients.data) return <LinearProgress />;

  const rows = patients.data ?? [];
  const items = queue.data ?? [];

  const pending = items.filter((q) => q.note.status === "pending_review");
  const returned = items.filter((q) => q.note.status === "returned");
  const stale = pending.filter((q) => now - new Date(q.note.updatedAt).getTime() >= DAY_MS);
  const flagged = rows.filter((r) => r.patient.labs.some((l) => l.flag));
  const inClinic = rows.filter((r) => r.patient.status.encounter === "Checked in" || r.patient.status.encounter === "Roomed" || r.patient.status.encounter === "In progress");
  const recent = (audit.data ?? []).slice(0, 8);

  return (
    <Box sx={{ display: "grid", gap: 2.5 }}>
      <StatGrid title="Today">
        <StatCard
          label="Notes to review"
          value={pending.length}
          tone="navy"
          to="/review?status=pending_review"
          icon={<AssignmentOutlined fontSize="small" />}
        />
        <StatCard
          label="Waiting over a day"
          value={stale.length}
          tone="orange"
          to="/review?status=pending_review"
          icon={<AssignmentOutlined fontSize="small" />}
        />
        <StatCard
          label="Returned to students"
          value={returned.length}
          tone="orangeSoft"
          to="/review?status=returned"
          icon={<ReplayOutlined fontSize="small" />}
        />
        <StatCard
          label="Patients in clinic"
          value={inClinic.length}
          tone="navySoft"
          to="/patients"
          icon={<PeopleAltOutlined fontSize="small" />}
        />
        <StatCard
          label="Flagged labs"
          value={flagged.length}
          tone="navy"
          to="/patients"
          icon={<ScienceOutlined fontSize="small" />}
        />
      </StatGrid>

      <Box sx={{ display: "grid", gap: 2.5, gridTemplateColumns: { xs: "1fr", lg: "1.4fr 1fr" } }}>
        <Panel title="Review queue" action={{ label: "Open queue", to: "/review?status=pending_review" }} accent>
          {queue.loading && !queue.data ? <LinearProgress /> : pending.length === 0 ? (
            <EmptyState title="Nothing waiting">Students' assessment notes will land here after they submit for signature.</EmptyState>
          ) : (
            <Table size="small" aria-label="Notes awaiting review">
              <TableHead>
                <TableRow>
                  <TableCell>Student</TableCell>
                  <TableCell>Patient</TableCell>
                  <TableCell>Waiting</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {pending.slice(0, 8).map((q) => (
                  <TableRow
                    key={q.note.id}
                    hover
                    component={RouterLink}
                    to={`/review/${q.note.id}`}
                    sx={{ textDecoration: "none", "&:hover td": { color: utep.navy } }}
                  >
                    <TableCell sx={{ fontWeight: 600 }}>{q.note.authorName}</TableCell>
                    <TableCell>{patientName(q.patient)}</TableCell>
                    <TableCell>{since(q.note.updatedAt, now)}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </Panel>

        <Panel title="Recent activity" action={{ label: "Full log", to: "/audit" }}>
          {audit.loading && !audit.data ? <LinearProgress /> : recent.length === 0 ? (
            <EmptyState title="No events yet">Chart views and note actions will show here.</EmptyState>
          ) : (
            <Box component="ul" sx={{ m: 0, pl: 0, listStyle: "none", display: "grid", gap: 1.25 }}>
              {recent.map((e) => (
                <Box component="li" key={e.id} sx={{ display: "grid", gap: 0.15 }}>
                  <Typography sx={{ fontSize: 14, fontWeight: 600, color: utep.navy }}>
                    {e.actorName} · {actionLabel(e.action, e.detail)}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    {e.entity} · {formatRelativeShort(e.timestamp)}
                    {e.result === "denied" ? " · denied" : ""}
                  </Typography>
                </Box>
              ))}
            </Box>
          )}
        </Panel>
      </Box>

      <Panel
        title="Students to check in with"
        subtitle={
          risk.data
            ? `No chart activity for ${risk.data.days} days, or an assigned chart with no note.`
            : "No chart activity for 7 days, or an assigned chart with no note."
        }
        action={{ label: "Activity report", to: "/teaching" }}
      >
        {risk.loading && !risk.data ? <LinearProgress /> : (risk.data?.students.length ?? 0) === 0 ? (
          <EmptyState title="No one is flagged">Students show up here after a week without opening a chart, or when an assigned chart has no submitted note.</EmptyState>
        ) : (
          <Table size="small" aria-label="Students to check in with">
            <TableHead>
              <TableRow>
                <TableCell>Student</TableCell>
                <TableCell>Why</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {risk.data?.students.slice(0, 12).map((student) => (
                <TableRow key={student.userId}>
                  <TableCell sx={{ fontWeight: 600 }}>{student.student}</TableCell>
                  <TableCell>{student.reasons.join(". ")}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </Panel>

      <Panel title="Patients with flagged labs" subtitle="High or low results on the current chart" action={{ label: "All patients", to: "/patients" }}>
        {flagged.length === 0 ? (
          <EmptyState title="No flagged labs">Out-of-range results will appear here.</EmptyState>
        ) : (
          <Table size="small" aria-label="Flagged labs">
            <TableHead>
              <TableRow>
                <TableCell>Patient</TableCell>
                <TableCell>Finding</TableCell>
                <TableCell>Visit</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {flagged.slice(0, 8).map((r) => {
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
                    <TableCell>
                      {lab ? `${lab.name} ${lab.value} ${lab.unit} (${lab.flag})` : "—"}
                    </TableCell>
                    <TableCell>{r.patient.status.encounter}</TableCell>
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>
        )}
      </Panel>
    </Box>
  );
}
