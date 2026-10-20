import { Alert, Box, Button, Chip, Paper, Table, TableBody, TableCell, TableHead, TableRow, Typography } from "@mui/material";
import { useNavigate } from "react-router-dom";
import type { ClinicalNote, EncounterStatus, Patient } from "../../../types";
import { listAppointments, listReferrals } from "../../../api/scheduling";
import { useSession } from "../../auth/AuthContext";
import { can } from "../../../utils/permissions";
import { formatDate, formatDateTime } from "../../../utils/format";
import { disciplineLabel } from "../../../utils/labels";
import { useAsync } from "../../../utils/useAsync";
import { utep } from "../../../theme/tokens";
import NotesList from "../../encounters/components/NotesList";
import VitalsChart from "./VitalsChart";

const FLOW: EncounterStatus[] = ["Scheduled", "Checked in", "In progress", "Checked out"];
const ADVANCE_LABEL: Partial<Record<EncounterStatus, string>> = {
  "Checked in": "Check in",
  "In progress": "Start visit",
  "Checked out": "Check out",
};

interface Props {
  patient: Patient;
  notes: ClinicalNote[];
  onAdvance: (next: EncounterStatus) => Promise<void>;
}

const card = { p: 2.5, borderRadius: "16px" } as const;
const titleSx = { color: utep.navy, fontSize: 18, mb: 1.5 } as const;

export default function SummaryTab({ patient: p, notes, onAdvance }: Props) {
  const navigate = useNavigate();
  const { user, activeRole } = useSession();
  const isAuthor = can(activeRole, "note:author");
  const appts = useAsync(() => listAppointments(p.id, activeRole), [p.id, activeRole]);
  const refs = useAsync(() => listReferrals(p.id, activeRole), [p.id, activeRole]);

  const idx = FLOW.indexOf(p.status.encounter);
  const next = idx >= 0 && idx < FLOW.length - 1 ? FLOW[idx + 1] : undefined;
  const needsCosign = next === "Checked out" && p.mode === "assessment" && !notes.some((n) => n.status === "cosigned");

  const mine = notes.filter((n) => n.authorId === user.id);
  const openNote = mine.find((n) => n.status === "draft" || n.status === "returned");
  const submitted = p.mode === "assessment" && mine.some((n) => n.status === "pending_review" || n.status === "cosigned");

  const noteButton = !isAuthor ? null : openNote ? (
    <Button variant="contained" color="secondary" onClick={() => navigate(`/patients/${p.id}/notes/${openNote.id}`)}>
      {openNote.status === "returned" ? "Revise returned note" : "Continue note"}
    </Button>
  ) : !submitted ? (
    <Button variant="contained" color="secondary" onClick={() => navigate(`/patients/${p.id}/notes/new`)}>Start note</Button>
  ) : null;

  const nextStep = (() => {
    if (!isAuthor) return null;
    if (openNote?.status === "returned") {
      return {
        severity: "error" as const,
        title: "Your instructor returned this note",
        body: "Open it, address the feedback, then sign and resubmit.",
        action: noteButton,
      };
    }
    if (openNote?.status === "draft") {
      return {
        severity: "info" as const,
        title: "You have a draft in progress",
        body: "Continue documenting, then sign and submit for review when you're ready.",
        action: noteButton,
      };
    }
    if (mine.some((n) => n.status === "pending_review")) {
      return {
        severity: "success" as const,
        title: "Note submitted — waiting for co-signature",
        body: "You can keep reviewing the chart. You'll edit again only if the note is returned.",
        action: null,
      };
    }
    if (mine.some((n) => n.status === "cosigned")) {
      return {
        severity: "success" as const,
        title: "Note co-signed",
        body: "This documentation is final. You can still add an addendum if something new comes up.",
        action: null,
      };
    }
    if (!submitted) {
      return {
        severity: "info" as const,
        title: p.mode === "assessment" ? "Next: document this visit" : "Practice documenting on this patient",
        body: p.mode === "assessment"
          ? "Review the summary below, then start a note. You'll pick an instructor when you submit."
          : "Practice notes aren't graded. Reset happens when an instructor restores the chart.",
        action: noteButton,
      };
    }
    return null;
  })();

  return (
    <Box sx={{ display: "flex", flexDirection: "column", gap: 2.5 }}>
      {nextStep && (
        <Alert
          severity={nextStep.severity}
          action={nextStep.action ? <Box sx={{ display: "flex", alignItems: "center", pl: 1 }}>{nextStep.action}</Box> : undefined}
          sx={{ alignItems: "center" }}
        >
          <Typography variant="subtitle2">{nextStep.title}</Typography>
          <Typography variant="body2">{nextStep.body}</Typography>
        </Alert>
      )}
      {needsCosign && isAuthor && (
        <Alert severity="info">You can check the patient out once your instructor co-signs your note.</Alert>
      )}

      <Paper sx={card}>
        <Box sx={{ display: "flex", alignItems: "center", gap: 1.5, flexWrap: "wrap", mb: 2 }}>
          <Box sx={{ flex: 1, minWidth: 200 }}>
            <Typography component="h2" variant="h6" sx={{ color: utep.navy }}>{p.encounter.type}</Typography>
            <Typography variant="body2" color="text.secondary">
              {formatDate(p.encounter.date)} · visit {p.status.encounter.toLowerCase()} · {p.status.careSetting.toLowerCase()}
            </Typography>
          </Box>
          {next && can(activeRole, "encounter:advance") && (
            <Button variant="outlined" disabled={needsCosign} onClick={() => onAdvance(next)}>
              {ADVANCE_LABEL[next]}
            </Button>
          )}
          {!nextStep?.action && noteButton}
        </Box>
        <Typography variant="subtitle2">Chief complaint</Typography>
        <Typography variant="body2" sx={{ mb: 1.5 }}>{p.chiefComplaint}</Typography>
        <Typography variant="subtitle2">History of present illness</Typography>
        <Typography variant="body2" sx={{ maxWidth: "75ch" }}>{p.hpi}</Typography>
      </Paper>

      <Box sx={{ display: "grid", gap: 2.5, gridTemplateColumns: { xs: "1fr", lg: "minmax(0, 1.7fr) minmax(280px, 1fr)" }, alignItems: "stretch" }}>
        <Paper sx={card}>
          <Typography component="h2" variant="h6" sx={titleSx}>Vitals</Typography>
          <VitalsChart patient={p} />
        </Paper>
        <Paper sx={card}>
          <Typography component="h2" variant="h6" sx={titleSx}>Diagnoses</Typography>
          {p.problems.length === 0 ? (
            <Typography variant="body2" color="text.secondary">No problems on the list.</Typography>
          ) : (
            <Box sx={{ display: "flex", flexDirection: "column", gap: 1.25 }}>
              {p.problems.map((pr) => (
                <Box key={pr.description} sx={{ p: 1.5, borderRadius: "12px", bgcolor: "#F7F8FB", border: `1px solid ${utep.line}` }}>
                  {pr.code && <Typography variant="caption" sx={{ fontWeight: 800, color: utep.orange, display: "block" }}>{pr.code}</Typography>}
                  <Typography variant="body2" sx={{ fontWeight: 700, color: utep.navy }}>{pr.description}</Typography>
                  {pr.since && <Typography variant="caption" color="text.secondary">Since {pr.since}</Typography>}
                </Box>
              ))}
            </Box>
          )}
        </Paper>
      </Box>

      <Box sx={{ display: "grid", gap: 2.5, gridTemplateColumns: { xs: "1fr", lg: "1fr 1fr" }, alignItems: "start" }}>
        <Paper sx={card}>
          <Typography component="h2" variant="h6" sx={titleSx}>Medications</Typography>
          {p.medications.length === 0 ? (
            <Typography variant="body2" color="text.secondary">No active medications.</Typography>
          ) : (
            <Box sx={{ overflowX: "auto" }}>
              <Table size="small">
                <TableHead>
                  <TableRow>
                    <TableCell>Name</TableCell>
                    <TableCell>Dose</TableCell>
                    <TableCell>Route</TableCell>
                    <TableCell>Frequency</TableCell>
                    <TableCell>Indication</TableCell>
                    <TableCell>Adherence</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {p.medications.map((m) => (
                    <TableRow key={m.id}>
                      <TableCell sx={{ fontWeight: 600 }}>{m.name}</TableCell>
                      <TableCell>{m.dose}</TableCell>
                      <TableCell>{m.route}</TableCell>
                      <TableCell>{m.frequency}</TableCell>
                      <TableCell>{m.indication ?? "—"}</TableCell>
                      <TableCell>{m.adherence ?? "Not documented"}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </Box>
          )}
        </Paper>

        <Paper sx={card}>
          <Typography component="h2" variant="h6" sx={titleSx}>Labs</Typography>
          {p.labs.length === 0 ? (
            <Typography variant="body2" color="text.secondary">None on file</Typography>
          ) : (
            <Box sx={{ overflowX: "auto" }}>
              <Table size="small">
                <TableHead>
                  <TableRow>
                    <TableCell>Test</TableCell>
                    <TableCell align="right">Result</TableCell>
                    <TableCell>Range</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {p.labs.map((l) => (
                    <TableRow key={l.id} sx={l.flag ? { bgcolor: utep.alertSoft } : undefined}>
                      <TableCell>{l.name}</TableCell>
                      <TableCell align="right" sx={{ fontWeight: l.flag ? 700 : 400, color: l.flag ? "error.main" : undefined }}>
                        {l.value} {l.unit}{l.flag ? ` ${l.flag}` : ""}
                      </TableCell>
                      <TableCell>{l.referenceRange}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </Box>
          )}
        </Paper>
      </Box>

      <Paper sx={card}>
        <Typography component="h2" variant="h6" sx={titleSx}>History</Typography>
        <Box sx={{ display: "grid", gap: 1.5, gridTemplateColumns: { md: "repeat(3, 1fr)" } }}>
          <Detail label="Family history" value={p.familyHistory} />
          <Detail label="Surgical history" value={p.surgicalHistory} />
          <Detail label="Social history" value={p.socialHistory} />
        </Box>
      </Paper>

      <Box sx={{ display: "grid", gap: 2.5, gridTemplateColumns: { md: "1fr 1fr" }, alignItems: "start" }}>
        <Paper sx={card}>
          <Typography component="h2" variant="h6" sx={titleSx}>Upcoming appointments</Typography>
          {(appts.data ?? []).length === 0 && <Typography variant="body2" color="text.secondary">None scheduled.</Typography>}
          {(appts.data ?? []).map((a) => (
            <Box key={a.id} sx={{ mb: 1.25 }}>
              <Typography variant="body2" sx={{ fontWeight: 700 }}>{formatDateTime(a.when)}</Typography>
              <Typography variant="body2">{a.kind}, {a.withWhom}</Typography>
            </Box>
          ))}
        </Paper>
        <Paper sx={card}>
          <Typography component="h2" variant="h6" sx={titleSx}>Referrals</Typography>
          {(refs.data ?? []).length === 0 && <Typography variant="body2" color="text.secondary">No referrals yet.</Typography>}
          {(refs.data ?? []).map((r) => (
            <Box key={r.id} sx={{ mb: 1.25 }}>
              <Box sx={{ display: "flex", gap: 1, alignItems: "center", flexWrap: "wrap" }}>
                <Typography variant="body2" sx={{ fontWeight: 700 }}>To {disciplineLabel[r.toDiscipline]}</Typography>
                {r.urgency === "urgent" && <Chip size="small" color="error" label="Urgent" />}
              </Box>
              <Typography variant="body2">{r.reason}</Typography>
            </Box>
          ))}
        </Paper>
      </Box>

      <Paper sx={card}>
        <Box sx={{ display: "flex", alignItems: "center", gap: 1.5, flexWrap: "wrap", mb: 1.5 }}>
          <Typography component="h2" variant="h6" sx={{ ...titleSx, mb: 0, flex: 1 }}>Notes on this encounter</Typography>
          {noteButton}
        </Box>
        <NotesList notes={notes} patientId={p.id} reviewer={!isAuthor} emptyAction={!notes.length ? noteButton : undefined} />
      </Paper>
    </Box>
  );
}

function Detail({ label, value }: { label: string; value: string }) {
  return (
    <Box>
      <Typography variant="subtitle2">{label}</Typography>
      <Typography variant="body2">{value}</Typography>
    </Box>
  );
}
