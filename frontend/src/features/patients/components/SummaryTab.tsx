import { useState } from "react";
import { Alert, Autocomplete, Box, Button, MenuItem, Paper, Stack, Table, TableBody, TableCell, TableHead, TableRow, TextField, Typography } from "@mui/material";
import { useNavigate } from "react-router-dom";
import type { AllergyCategory, ClinicalNote, EncounterStatus, LungSoundFinding, LungSoundLocation, Patient } from "../../../types";
import { listAppointments } from "../../../api/scheduling";
import { addAllergy, addLungSound, addVital, markLungSoundEnteredInError, markVitalEnteredInError, removeAllergy } from "../../../api/chart";
import VitalsChart from "./VitalsChart";
import PatientReportedCard from "./PatientReportedCard";
import { useSession } from "../../auth/useSession";
import { can } from "../../../utils/permissions";
import { canEditSection } from "../../chart/access";
import { formatDate, formatDateTime } from "../../../utils/format";
import { useAsync } from "../../../utils/useAsync";
import { utep } from "../../../theme/tokens";
import { simulationNoteAction } from "../simulation";

const FLOW: EncounterStatus[] = ["Scheduled", "Checked in", "Roomed", "In progress", "Checked out"];
const ADVANCE_LABEL: Partial<Record<EncounterStatus, string>> = {
  "Checked in": "Check in",
  Roomed: "Room patient",
  "In progress": "Start visit",
  "Checked out": "Check out",
};
const VITAL_LABELS = ["BP", "Pulse", "Pain", "Temperature", "Respiratory rate", "SpO2", "Weight"];
const LUNG_LOCATIONS: LungSoundLocation[] = ["RUL", "RML", "RLL", "LUL", "LLL"];
const LUNG_FINDINGS: LungSoundFinding[] = ["clear", "crackles", "wheeze", "diminished", "rhonchi", "other"];

interface Props {
  patient: Patient;
  notes: ClinicalNote[];
  onAdvance: (next: EncounterStatus) => Promise<void>;
  onChange: (patient: Patient) => void;
}

const card = { p: 2.5, borderRadius: "16px" } as const;
const titleSx = { color: utep.navy, fontSize: 18, mb: 1.5 } as const;

const CATEGORIES: { id: AllergyCategory; label: string }[] = [
  { id: "medication", label: "Medication" },
  { id: "food", label: "Food" },
  { id: "environmental", label: "Environmental" },
];

export default function SummaryTab({ patient: p, notes, onAdvance, onChange }: Props) {
  const navigate = useNavigate();
  const { user, activeRole } = useSession();
  const isAuthor = can(activeRole, "note:author");
  const appts = useAsync(() => listAppointments(p.id, activeRole), [p.id, activeRole]);
  const [allergy, setAllergy] = useState({ substance: "", category: "medication" as AllergyCategory, reaction: "" });
  const [vital, setVital] = useState({ label: "", value: "" });
  const [lung, setLung] = useState({ location: "RUL" as LungSoundLocation, finding: "clear" as LungSoundFinding, notes: "" });
  const [error, setError] = useState("");
  const [now] = useState(() => Date.now());

  const idx = FLOW.indexOf(p.status.encounter);
  const next = idx >= 0 && idx < FLOW.length - 1 ? FLOW[idx + 1] : undefined;
  const needsCosign = next === "Checked out" && p.mode === "assessment" && !notes.some((n) => n.status === "cosigned");

  const mine = notes.filter((n) => n.authorId === user.id);
  const openNote = mine.find((n) => n.status === "draft" || n.status === "returned");
  const submitted = p.mode === "assessment" && mine.some((n) => n.status === "pending_review" || n.status === "cosigned");
  const simAction = p.mode === "simulation" ? simulationNoteAction(p, notes, user.id) : undefined;

  const noteButton = simAction !== undefined ? (simAction ? (
    <Button variant="contained" color="secondary" onClick={() => navigate(simAction.href)}>{simAction.label}</Button>
  ) : null) : !isAuthor ? null : openNote ? (
    <Button variant="contained" color="secondary" onClick={() => navigate(`/patients/${p.id}/notes/${openNote.id}`)}>
      {openNote.status === "returned" ? "Revise returned note" : "Continue note"}
    </Button>
  ) : !submitted ? (
    <Button variant="contained" color="secondary" onClick={() => navigate(`/patients/${p.id}/notes/new`)}>Start note</Button>
  ) : null;

  const nextStep = (() => {
    if (p.mode === "simulation") {
      const phase = p.simulationPhase ?? "waiting_vitals";
      if (phase === "waiting_vitals") {
        return {
          severity: "info" as const,
          title: "Waiting for vitals",
          body: "The nurse records vitals and lung sounds. The visit note opens after that.",
          action: null,
        };
      }
      if (simAction) {
        return {
          severity: "info" as const,
          title: phase === "closed" ? "Visit note is closed" : "Ready for the visit note",
          body: phase === "closed"
            ? "A clarification is a new note. The signed visit note stays closed."
            : p.viewerStation === "pharmacist"
              ? "Write the visit note, and use Medications → Fill verification to verify or hold submitted fills."
              : "The pharmacist or provider writes the note. The provider signs it closed. Pharmacists can also verify fills on the Medications tab.",
          action: noteButton,
        };
      }
      return null;
    }
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

  const upcoming = [...(appts.data ?? [])].sort((a, b) => a.when.localeCompare(b.when));
  const nextAppointment = upcoming.find((item) => new Date(item.when).getTime() >= now) ?? upcoming[0];

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
        <Typography variant="body2">{p.chiefComplaint || "Not documented"}</Typography>
      </Paper>

      {error && <Alert severity="error" onClose={() => setError("")}>{error}</Alert>}

      {(p.unit || p.room || p.bed) && (
        <Paper sx={card}>
          <Typography component="h2" variant="h6" sx={titleSx}>Location</Typography>
          <Typography variant="body2">{[p.unit, p.room && `Room ${p.room}`, p.bed && `Bed ${p.bed}`].filter(Boolean).join(", ")}</Typography>
        </Paper>
      )}

      {(p.insurance?.payer || p.insurance?.memberId || p.insurance?.groupNumber || p.insurance?.notes) && (
      <Paper sx={card}>
        <Typography component="h2" variant="h6" sx={titleSx}>Insurance</Typography>
        <Stack spacing={0.5}>
          {p.insurance.payer && <Typography variant="body2"><strong>Payer:</strong> {p.insurance.payer}</Typography>}
          {p.insurance.memberId && <Typography variant="body2"><strong>Member ID:</strong> {p.insurance.memberId}</Typography>}
          {p.insurance.groupNumber && <Typography variant="body2"><strong>Group:</strong> {p.insurance.groupNumber}</Typography>}
          {p.insurance.notes && <Typography variant="body2"><strong>Notes:</strong> {p.insurance.notes}</Typography>}
        </Stack>
      </Paper>
      )}

      {(p.emergencyContact?.name || p.emergencyContact?.phone || p.emergencyContact?.relationship) && (
      <Paper sx={card}>
        <Typography component="h2" variant="h6" sx={titleSx}>Emergency contact</Typography>
        <Stack spacing={0.5}>
          {p.emergencyContact.name && <Typography variant="body2"><strong>Name:</strong> {p.emergencyContact.name}</Typography>}
          {p.emergencyContact.relationship && (
            <Typography variant="body2"><strong>Relationship:</strong> {p.emergencyContact.relationship}</Typography>
          )}
          {p.emergencyContact.phone && <Typography variant="body2"><strong>Phone:</strong> {p.emergencyContact.phone}</Typography>}
        </Stack>
      </Paper>
      )}

      {(p.codeStatus || p.advanceDirectiveNotes || p.hipaaOnFile || p.hipaaNote) && (
      <Paper sx={card}>
        <Typography component="h2" variant="h6" sx={titleSx}>Directives & consent</Typography>
        <Stack spacing={0.5}>
          {p.codeStatus && <Typography variant="body2"><strong>Code status:</strong> {p.codeStatus}</Typography>}
          {p.advanceDirectiveNotes && (
            <Typography variant="body2"><strong>Advance directives:</strong> {p.advanceDirectiveNotes}</Typography>
          )}
          <Typography variant="body2">
            <strong>HIPAA:</strong>{" "}
            {p.hipaaOnFile
              ? `On file${p.hipaaSignedAt ? ` (${formatDate(p.hipaaSignedAt)})` : ""}`
              : "Not on file"}
          </Typography>
          {p.hipaaNote && <Typography variant="body2"><strong>Consent note:</strong> {p.hipaaNote}</Typography>}
        </Stack>
      </Paper>
      )}

      <Box sx={{ display: "grid", gap: 2.5, gridTemplateColumns: { xs: "1fr", lg: "1fr 1fr" }, alignItems: "start" }}>
        <Paper sx={card}>
          <Typography component="h2" variant="h6" sx={titleSx}>Allergies</Typography>
          {CATEGORIES.map((category) => {
            const rows = p.allergies.filter((item) => (item.category ?? "medication") === category.id);
            return (
              <Box key={category.id} sx={{ mb: 1.5 }}>
                <Typography variant="subtitle2">{category.label}</Typography>
                <Typography variant="body2">
                  {rows.length
                    ? rows.map((item) => item.reaction ? `${item.substance} (${item.reaction})` : item.substance).join(", ")
                    : "None documented"}
                </Typography>
                {canEditSection(activeRole, p, "allergies") && rows.map((item) => item.id && (
                  <Button key={item.id} size="small" color="error" onClick={async () => {
                    try { onChange(await removeAllergy(activeRole, p.id, item.id!)); } catch (e) { setError((e as Error).message); }
                  }}>Remove {item.substance}</Button>
                ))}
              </Box>
            );
          })}
          {canEditSection(activeRole, p, "allergies") && (
            <Stack direction={{ xs: "column", sm: "row" }} spacing={1}>
              <TextField size="small" label="Substance" value={allergy.substance} onChange={(e) => setAllergy({ ...allergy, substance: e.target.value })} />
              <TextField size="small" label="Reaction" value={allergy.reaction} onChange={(e) => setAllergy({ ...allergy, reaction: e.target.value })} />
              <TextField select size="small" label="Category" value={allergy.category} onChange={(e) => setAllergy({ ...allergy, category: e.target.value as AllergyCategory })}>
                {CATEGORIES.map((item) => <MenuItem key={item.id} value={item.id}>{item.label}</MenuItem>)}
              </TextField>
              <Button variant="outlined" onClick={async () => {
                try {
                  onChange(await addAllergy(activeRole, p.id, allergy));
                  setAllergy({ substance: "", category: "medication", reaction: "" });
                } catch (e) { setError((e as Error).message); }
              }}>Add</Button>
            </Stack>
          )}
        </Paper>
        <Paper sx={card}>
          <Typography component="h2" variant="h6" sx={titleSx}>Current vitals</Typography>
          <LatestVitals patient={p} />
          <Box sx={{ mt: 2 }}>
            <VitalsChart patient={p} />
          </Box>
          <VitalsHistory
            patient={p}
            canMark={canEditSection(activeRole, p, "vitals")}
            onMark={async (id) => {
              try { onChange(await markVitalEnteredInError(activeRole, p.id, id)); }
              catch (e) { setError((e as Error).message); }
            }}
          />
          {canEditSection(activeRole, p, "vitals") && (
            <Stack direction={{ xs: "column", sm: "row" }} spacing={1} sx={{ mt: 1.5 }}>
              <Autocomplete
                freeSolo
                options={VITAL_LABELS}
                inputValue={vital.label}
                onInputChange={(_, value) => setVital({ ...vital, label: value })}
                renderInput={(params) => <TextField {...params} size="small" label="Label" placeholder="Pain" />}
                sx={{ minWidth: 160 }}
              />
              <TextField size="small" label="Value" placeholder={vital.label === "Pain" ? "0–10" : ""} value={vital.value} onChange={(e) => setVital({ ...vital, value: e.target.value })} />
              <Button variant="outlined" onClick={async () => {
                try {
                  onChange(await addVital(activeRole, p.id, vital));
                  setVital({ label: "", value: "" });
                } catch (e) { setError((e as Error).message); }
              }}>Add</Button>
            </Stack>
          )}
        </Paper>
      </Box>

      <Paper sx={card}>
        <Typography component="h2" variant="h6" sx={titleSx}>Lung sounds</Typography>
        {(p.lungSounds ?? []).filter((row) => (row.status ?? "recorded") === "recorded").length === 0 ? (
          <Typography variant="body2" color="text.secondary">None documented</Typography>
        ) : (
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell>Location</TableCell>
                <TableCell>Finding</TableCell>
                <TableCell>Notes</TableCell>
                <TableCell>Recorded</TableCell>
                {canEditSection(activeRole, p, "lung_sounds") && <TableCell />}
              </TableRow>
            </TableHead>
            <TableBody>
              {[...(p.lungSounds ?? [])]
                .filter((row) => (row.status ?? "recorded") === "recorded")
                .map((row) => (
                  <TableRow key={row.id ?? `${row.location}-${row.finding}-${row.recordedAt}`}>
                    <TableCell>{row.location}</TableCell>
                    <TableCell sx={{ textTransform: "capitalize" }}>{row.finding}</TableCell>
                    <TableCell>{row.notes || "—"}</TableCell>
                    <TableCell>
                      {row.recordedAt ? formatDateTime(row.recordedAt) : "—"}
                      {row.recordedByName ? ` · ${row.recordedByName}` : ""}
                    </TableCell>
                    {canEditSection(activeRole, p, "lung_sounds") && row.id && (
                      <TableCell>
                        <Button
                          size="small"
                          color="error"
                          onClick={async () => {
                            try { onChange(await markLungSoundEnteredInError(activeRole, p.id, row.id!)); }
                            catch (e) { setError((e as Error).message); }
                          }}
                        >
                          Entered in error
                        </Button>
                      </TableCell>
                    )}
                  </TableRow>
                ))}
            </TableBody>
          </Table>
        )}
        {canEditSection(activeRole, p, "lung_sounds") && (
          <Stack direction={{ xs: "column", sm: "row" }} spacing={1} sx={{ mt: 1.5, alignItems: "flex-start" }}>
            <TextField
              select size="small" label="Location" value={lung.location}
              onChange={(e) => setLung({ ...lung, location: e.target.value as LungSoundLocation })}
              sx={{ minWidth: 120 }}
            >
              {LUNG_LOCATIONS.map((item) => <MenuItem key={item} value={item}>{item}</MenuItem>)}
            </TextField>
            <TextField
              select size="small" label="Finding" value={lung.finding}
              onChange={(e) => setLung({ ...lung, finding: e.target.value as LungSoundFinding })}
              sx={{ minWidth: 140 }}
            >
              {LUNG_FINDINGS.map((item) => <MenuItem key={item} value={item}>{item}</MenuItem>)}
            </TextField>
            <TextField
              size="small" label="Notes" value={lung.notes}
              onChange={(e) => setLung({ ...lung, notes: e.target.value })}
              sx={{ flex: 1, minWidth: 160 }}
            />
            <Button variant="outlined" onClick={async () => {
              try {
                onChange(await addLungSound(activeRole, p.id, {
                  location: lung.location,
                  finding: lung.finding,
                  notes: lung.notes.trim() || undefined,
                }));
                setLung({ location: "RUL", finding: "clear", notes: "" });
              } catch (e) { setError((e as Error).message); }
            }}>Add</Button>
          </Stack>
        )}
        {(p.lungSounds ?? []).some((row) => (row.status ?? "recorded") === "recorded") && (
          <Typography variant="caption" color="text.secondary" sx={{ display: "block", mt: 1.5 }}>
            Suggested Objective text:{" "}
            {[...(p.lungSounds ?? [])]
              .filter((row) => (row.status ?? "recorded") === "recorded")
              .map((row) => `${row.location} ${row.finding}${row.notes ? ` (${row.notes})` : ""}`)
              .join("; ")}.
          </Typography>
        )}
      </Paper>

      <Box sx={{ display: "grid", gap: 2.5, gridTemplateColumns: { xs: "1fr", lg: "minmax(0, 1.7fr) minmax(280px, 1fr)" }, alignItems: "stretch" }}>
        <Paper sx={card}>
          <Typography component="h2" variant="h6" sx={titleSx}>Recent labs</Typography>
          {p.labs.length === 0 ? <Typography variant="body2" color="text.secondary">None on file</Typography> : (
            <Table size="small">
              <TableBody>
                {[...p.labs].slice(-5).reverse().map((lab) => (
                  <TableRow key={lab.id}>
                    <TableCell>{lab.name}</TableCell>
                    <TableCell>{lab.value} {lab.unit}</TableCell>
                    <TableCell>{formatDate(lab.collectedAt)}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
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

      {nextAppointment && (
      <Paper sx={card}>
        <Typography component="h2" variant="h6" sx={titleSx}>Next appointment</Typography>
        <Typography variant="body2" sx={{ fontWeight: 700 }}>{formatDateTime(nextAppointment.when)}</Typography>
        <Typography variant="body2">{nextAppointment.kind}, {nextAppointment.withWhom}</Typography>
      </Paper>
      )}
      <PatientReportedCard patientId={p.id} />
    </Box>
  );
}

function visibleVitals(patient: Patient) {
  return patient.vitals.filter((item) => item.status !== "entered_in_error");
}

function VitalsHistory({
  patient, canMark, onMark,
}: {
  patient: Patient;
  canMark: boolean;
  onMark: (id: string) => Promise<void>;
}) {
  const rows = [...patient.vitals].sort((a, b) => (b.recordedAt ?? "").localeCompare(a.recordedAt ?? ""));
  if (rows.length === 0) return null;
  return (
    <Table size="small" sx={{ mt: 2 }} aria-label="Vitals history">
      <TableHead>
        <TableRow>
          <TableCell>Vital</TableCell>
          <TableCell>Value</TableCell>
          <TableCell>Recorded</TableCell>
          <TableCell />
        </TableRow>
      </TableHead>
      <TableBody>
        {rows.map((item) => {
          const mistake = item.status === "entered_in_error";
          return (
            <TableRow key={item.id ?? `${item.label}-${item.recordedAt}`}>
              <TableCell>{item.label}</TableCell>
              <TableCell sx={{ textDecoration: mistake ? "line-through" : "none" }}>{item.value}</TableCell>
              <TableCell>
                {item.recordedAt ? formatDateTime(item.recordedAt) : "On file"}
                {item.recordedByName ? ` · ${item.recordedByName}` : ""}
                {mistake ? " · entered in error" : ""}
              </TableCell>
              <TableCell align="right">
                {canMark && item.id && !mistake && (
                  <Button size="small" color="error" onClick={() => onMark(item.id!)}>Entered in error</Button>
                )}
              </TableCell>
            </TableRow>
          );
        })}
      </TableBody>
    </Table>
  );
}

function LatestVitals({ patient }: { patient: Patient }) {
  const latest = new Map<string, (typeof patient.vitals)[number]>();
  for (const item of visibleVitals(patient)) {
    const current = latest.get(item.label);
    const stamp = item.recordedAt ?? "";
    if (!current || stamp >= (current.recordedAt ?? "")) latest.set(item.label, item);
  }
  const rows = [...latest.values()];
  if (rows.length === 0) return <Typography variant="body2" color="text.secondary">No vitals recorded.</Typography>;
  return (
    <Stack spacing={0.5}>
      {rows.map((item) => (
        <Typography key={item.label} variant="body2"><b>{item.label}:</b> {item.value}</Typography>
      ))}
    </Stack>
  );
}

