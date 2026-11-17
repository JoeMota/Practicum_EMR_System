import { useCallback, useEffect, useRef, useState } from "react";
import {
  Alert, Autocomplete, Box, Breadcrumbs, Button, Checkbox, Dialog, DialogActions, DialogContent, DialogContentText, DialogTitle,
  FormControlLabel,
  Divider, LinearProgress, Link, MenuItem, Paper, Stack, TextField, Typography,
} from "@mui/material";
import { Link as RouterLink, useNavigate, useParams, useSearchParams } from "react-router-dom";
import type { ClinicalNote, CptSelection, IcdCode, Patient, User } from "../../types";
import { getPatient } from "../../api/patients";
import { addAddendum, checkInsertedDose, createDraft, getNote, listNotesForPatient, saveDraft, signNote, suggestSection } from "../../api/notes";
import { getCourse, listInstructors } from "../../api/courses";
import { listNoteTemplates } from "../../api/templates";
import { getChartGradingGuide } from "../../api/cases";
import { useSession } from "../auth/useSession";
import { formatDate, formatTime } from "../../utils/format";
import { listCpt } from "../../api/reference";
import { useAsync } from "../../utils/useAsync";
import NoteStatusChip from "../../components/NoteStatusChip";
import PageError from "../../components/PageError";
import PatientBanner from "../patients/components/PatientBanner";
import ChartReference from "../patients/components/ChartReference";
import NoteFields from "./components/NoteFields";
import NoteProgress from "./components/NoteProgress";
import FeedbackThread from "./components/FeedbackThread";
import Addenda from "./components/Addenda";
import CourseRubricPanel from "./components/CourseRubricPanel";
import AnswerKeyPanel from "./components/AnswerKeyPanel";
import { defaultTemplateFor, diagnosesFromPatient, prefillFromPatient, templateName, templatesFor, TEMPLATES, type NoteTemplate } from "./noteTemplates";
import { suggestionsFor } from "./suggestionPacks";

type SaveState = "idle" | "saving" | "saved" | "error";

/** Survives StrictMode remount so /notes/new doesn't POST two drafts. */
const creatingDraftKeys = new Set<string>();

export default function NoteEditorPage() {
  const { patientId = "", noteId = "new" } = useParams();
  const [search] = useSearchParams();
  const draftKind = search.get("kind") === "clarification" ? "clarification" : "visit";
  const navigate = useNavigate();
  const { user, activeRole, discipline, courseId } = useSession();

  const [patient, setPatient] = useState<Patient>();
  const [note, setNote] = useState<ClinicalNote>();
  const [instructors, setInstructors] = useState<User[]>([]);
  const [loadError, setLoadError] = useState<Error>();

  const [templateId, setTemplateId] = useState<string>(defaultTemplateFor(discipline));
  const savedTemplates = useAsync(() => listNoteTemplates(activeRole, courseId), [activeRole, courseId]);
  const [content, setContent] = useState<Record<string, string>>({});
  const [diagnoses, setDiagnoses] = useState<IcdCode[]>([]);
  const [cptCodes, setCptCodes] = useState<CptSelection[]>([]);
  const [cptOptions, setCptOptions] = useState<IcdCode[]>([]);
  const [routedToId, setRoutedToId] = useState("");

  const [saveState, setSaveState] = useState<SaveState>("idle");
  const [pending, setPending] = useState(false);
  const [savedAt, setSavedAt] = useState<string>();
  const [error, setError] = useState("");
  const [showErrors, setShowErrors] = useState(false);
  const [confirmOpen, setConfirmOpen] = useState(false);
  const course = useAsync(() => (courseId ? getCourse(courseId) : Promise.resolve(undefined)), [courseId]);
  const [suggestion, setSuggestion] = useState("");
  const [doseNotice, setDoseNotice] = useState("");
  const [doseFlags, setDoseFlags] = useState<{ code: string; message: string }[]>([]);
  const [doseAck, setDoseAck] = useState<string[]>([]);
  const guide = useAsync(
    () => (patientId && activeRole !== "student" ? getChartGradingGuide(activeRole, patientId) : Promise.resolve({ criteria: [], source: "course" as const })),
    [activeRole, patientId],
  );
  const version = useRef(0);
  const hydrate = (n: ClinicalNote) => {
    setNote(n);
    version.current = n.version;
    setTemplateId(n.templateId);
    setContent(n.content);
    setDiagnoses(n.diagnoses);
    setCptCodes(n.cptCodes ?? []);
    setRoutedToId(n.routedToId ?? "");
  };

  useEffect(() => {
    let alive = true;
    (async () => {
      try {
        const p = await getPatient(activeRole, patientId);
        if (!alive) return;
        setPatient(p);
        const people = await listInstructors(courseId);
        if (!alive) return;
        setInstructors(people);

        if (noteId === "new") {
          const key = `${user.id}:${patientId}:${draftKind}`;
          if (creatingDraftKeys.has(key)) return;
          creatingDraftKeys.add(key);
          try {
            const existing = (await listNotesForPatient(activeRole, patientId)).find(
              (n) => (n.kind ?? "visit") === draftKind
                && (n.status === "draft" || n.status === "returned")
                && (draftKind === "visit" || n.authorId === user.id),
            );
            const n = existing ?? (await createDraft(discipline ?? "pharmacy", p, defaultTemplateFor(discipline), activeRole, draftKind));
            if (!alive) return;
            navigate(`/patients/${patientId}/notes/${n.id}`, { replace: true });
          } finally {
            creatingDraftKeys.delete(key);
          }
          return;
        }
        const n = await getNote(activeRole, noteId);
        if (!alive) return;
        hydrate(n);
      } catch (e) {
        if (alive) setLoadError(e as Error);
      }
    })();
    return () => { alive = false; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [patientId, noteId, draftKind]);

  const latest = useRef({ templateId, content, diagnoses, cptCodes, routedToId });
  useEffect(() => {
    latest.current = { templateId, content, diagnoses, cptCodes, routedToId };
  }, [templateId, content, diagnoses, cptCodes, routedToId]);
  const changeSeq = useRef(0);
  const savedSeq = useRef(0);
  const saving = useRef(false);

  const clinician = patient?.mode === "simulation" && (patient.viewerStation === "pharmacist" || patient.viewerStation === "provider");
  const editable = Boolean(
    note && !note.bodyLocked && (note.status === "draft" || note.status === "returned")
    && (note.authorId === user.id || (clinician && (note.kind ?? "visit") === "visit")),
  );

  const save = useCallback(async (): Promise<boolean> => {
    if (!note || saving.current) return false;
    const seq = changeSeq.current;
    if (seq === savedSeq.current) return true;
    saving.current = true;
    setSaveState("saving");
    try {
      const res = await saveDraft(note.id, version.current, {
        ...latest.current, routedToId: latest.current.routedToId || undefined,
      }, activeRole);
      version.current = res.version;
      savedSeq.current = seq;
      setPending(changeSeq.current !== seq);
      setSavedAt(res.updatedAt);
      setSaveState("saved");
      return true;
    } catch (e) {
      setSaveState("error");
      setError((e as Error).message);
      return false;
    } finally {
      saving.current = false;
    }
  }, [note, activeRole]);

  useEffect(() => {
    if (!editable || !note || note.routedToId || !routedToId) return;
    changeSeq.current += 1;
    void save();
  }, [editable, note, routedToId, save]);

  const markDirty = () => {
    changeSeq.current += 1;
    setPending(true);
    setSaveState((s) => (s === "error" ? s : "idle"));
  };

  useEffect(() => {
    if (!editable || changeSeq.current === savedSeq.current) return;
    const t = setTimeout(save, 1200);
    return () => clearTimeout(t);
  }, [content, diagnoses, cptCodes, templateId, routedToId, editable, save]);

  useEffect(() => {
    const handler = (e: BeforeUnloadEvent) => {
      if (changeSeq.current !== savedSeq.current) e.preventDefault();
    };
    window.addEventListener("beforeunload", handler);
    return () => window.removeEventListener("beforeunload", handler);
  }, []);

  const setField = (id: string, next: string | ((prev: string) => string)) => {
    markDirty();
    setContent((c) => ({ ...c, [id]: typeof next === "function" ? next(c[id] ?? "") : next }));
  };

  const needsRoute = note?.mode === "assessment" && !routedToId;

  useEffect(() => {
    listCpt().then(setCptOptions).catch(() => setCptOptions([]));
  }, []);

  const trySign = () => {
    setShowErrors(true);
    if (needsRoute) {
      document.getElementById("route-select")?.focus();
      return;
    }
    setConfirmOpen(true);
  };

  const doSign = async () => {
    setConfirmOpen(false);
    // Flush any pending field edits, then sign against that version.
    changeSeq.current += 1;
    if (!(await save())) return;
    try {
      hydrate(await signNote(note!.id, version.current, activeRole));
      setShowErrors(false);
      savedSeq.current = changeSeq.current;
    } catch (e) {
      setError((e as Error).message);
    }
  };

  if (loadError) return <PageError error={loadError} />;
  if (!patient || !note) return <LinearProgress aria-label="Loading note" />;

  const isAssessment = note.mode === "assessment";
  const isSimulation = note.mode === "simulation";
  const reviewer = instructors.find((i) => i.id === (note.routedToId ?? routedToId));
  const errorSet = undefined;
  const choices: NoteTemplate[] = [
    ...templatesFor(discipline),
    ...(savedTemplates.data ?? [])
      .filter((row) => row.discipline === discipline)
      .map((row) => ({
        id: row.id,
        name: row.sensitive ? `${row.name} (sensitive)` : row.name,
        disciplines: [row.discipline],
        sections: row.sections,
      })),
  ];
  const current = choices.find((item) => item.id === templateId);

  return (
    <Stack spacing={2}>
      <Breadcrumbs aria-label="Breadcrumb">
        <Link component={RouterLink} to="/patients" underline="hover">My patients</Link>
        <Link component={RouterLink} to={`/patients/${patient.id}`} underline="hover">{patient.lastName}, {patient.firstName}</Link>
        <Typography color="text.primary">{current?.name ?? templateName(templateId)}</Typography>
      </Breadcrumbs>

      <PatientBanner patient={patient} compact />

      <Box sx={{ display: "grid", gap: 2.5, gridTemplateColumns: { xs: "1fr", lg: "1fr 340px" }, alignItems: "start" }}>
        {/* Editor */}
        <Paper component="article" aria-label="Note" sx={{ p: { xs: 2, md: 3 } }}>
          <Box sx={{ display: "flex", alignItems: "center", gap: 1.5, flexWrap: "wrap", mb: 2.5 }}>
            <Box sx={{ flex: 1, minWidth: 220 }}>
              <Typography component="h2" variant="h5">{current?.name ?? templateName(templateId)}</Typography>
              <Typography variant="body2" color="text.secondary">
                {patient.encounter.type}, {note.authorName}
              </Typography>
            </Box>
            <NoteStatusChip status={note.status} />
            {editable && note.status === "draft" && choices.length > 1 && (
              <TextField
                select size="small" label="Template" value={templateId} sx={{ minWidth: 240 }}
                onChange={(e) => {
                  const next = e.target.value;
                  markDirty();
                  setTemplateId(next);
                  const chosen = choices.find((item) => item.id === next);
                  const seeded = prefillFromPatient(next, patient, chosen);
                  setContent((prev) => {
                    const merged = { ...seeded };
                    for (const [k, v] of Object.entries(prev)) {
                      if (v?.trim()) merged[k] = v;
                    }
                    return merged;
                  });
                  setDiagnoses((prev) => (prev.length ? prev : diagnosesFromPatient(patient)));
                }}
              >
                {choices.map((t) => <MenuItem key={t.id} value={t.id}>{t.name}</MenuItem>)}
              </TextField>
            )}
          </Box>

          {note.status === "returned" && (
            <Alert severity="error" sx={{ mb: 2.5 }}>
              <Typography variant="subtitle2" sx={{ mb: 1 }}>Your instructor returned this note. Revise it and resubmit.</Typography>
              <FeedbackThread items={note.feedback.filter((item) => !item.sectionId)} />
            </Alert>
          )}
          {note.status === "pending_review" && (
            <Alert severity="info" sx={{ mb: 2.5 }}>
              Submitted to {reviewer?.fullName ?? "your instructor"}. You can edit again only if it's returned.
            </Alert>
          )}
          {note.status === "cosigned" && note.feedback.some((item) => !item.sectionId) && (
            <Alert severity="success" sx={{ mb: 2.5 }}><FeedbackThread items={note.feedback.filter((item) => !item.sectionId)} /></Alert>
          )}
          {editable && note.status === "draft" && (patient.prefillSections ?? []).length > 0 && (
            <Alert severity="info" icon={false} sx={{ mb: 2.5 }}>
              Sections your instructor turned on were copied into this note. Name, date of birth, and MRN stay in the header.
            </Alert>
          )}
          {error && <Alert severity="error" onClose={() => setError("")} sx={{ mb: 2.5 }}>{error}</Alert>}

          <Box sx={{ mb: 2.5, p: 1.5, borderRadius: 1, bgcolor: "rgba(14,34,80,0.04)" }}>
            <Typography variant="subtitle2">{patient.lastName}, {patient.firstName}</Typography>
            <Typography variant="body2" color="text.secondary">
              DOB {formatDate(patient.dob)} · MRN {patient.mrn}
            </Typography>
          </Box>

          {editable && course.data?.aiAssist && course.data?.aiProviderConfigured && (
            <Alert severity="info" sx={{ mb: 2 }} action={
              <Button color="inherit" size="small" onClick={async () => {
                const section = (TEMPLATES[templateId as keyof typeof TEMPLATES]?.sections[0]?.id) || "N";
                try {
                  const result = await suggestSection(activeRole, note.id, section);
                  setSuggestion(result.suggestion);
                  setDoseFlags([]);
                  setDoseAck([]);
                } catch (e) {
                  setError((e as Error).message);
                }
              }}>Suggest</Button>
            }>
              {suggestion || "Ask for a suggestion for the first section. Nothing is saved until you insert it."}
              {suggestion && (
                <Button sx={{ ml: 1 }} size="small" onClick={async () => {
                  const section = TEMPLATES[templateId as keyof typeof TEMPLATES]?.sections[0];
                  const field = section?.fields[0]?.id;
                  if (!field || !note) return;
                  try {
                    const check = await checkInsertedDose(activeRole, note.id, suggestion, doseAck);
                    if (check.blocked) {
                      setDoseFlags(check.flags);
                      setError(check.flags[0]?.message || "This dose is blocked for this class.");
                      return;
                    }
                    if (check.needsAcknowledgement) {
                      setDoseFlags(check.flags);
                      setError("Confirm the dose warning before inserting it.");
                      return;
                    }
                    markDirty();
                    setContent((prev) => ({ ...prev, [field]: prev[field] ? `${prev[field]}\n${suggestion}` : suggestion }));
                    setDoseNotice(check.flags.map((flag) => flag.message).join(" "));
                    setSuggestion("");
                    setDoseFlags([]);
                    setDoseAck([]);
                    setError("");
                  } catch (e) {
                    setError((e as Error).message);
                  }
                }}>Insert</Button>
              )}
              {doseFlags.length > 0 && (
                <FormControlLabel
                  sx={{ display: "flex", mt: 1 }}
                  control={
                    <Checkbox
                      checked={doseAck.length > 0}
                      onChange={(event) => setDoseAck(event.target.checked ? doseFlags.map((flag) => flag.code) : [])}
                    />
                  }
                  label="I reviewed this dose warning"
                />
              )}
            </Alert>
          )}
          {doseNotice && <Alert severity="warning" sx={{ mb: 2 }} onClose={() => setDoseNotice("")}>{doseNotice}</Alert>}
          {editable && (
            <Stack direction="row" spacing={1} sx={{ mb: 2, flexWrap: "wrap" }}>
              {suggestionsFor(discipline).map((line) => (
                <Button key={line} size="small" variant="outlined" onClick={() => {
                  const template = TEMPLATES[templateId as keyof typeof TEMPLATES];
                  const field = template?.sections[0]?.fields.find((item) => item.kind === "textarea")?.id;
                  if (!field) return;
                  markDirty();
                  setContent((prev) => ({ ...prev, [field]: prev[field] ? `${prev[field]} ${line}` : line }));
                }}>{line.slice(0, 42)}</Button>
              ))}
            </Stack>
          )}

          <NoteFields
            templateId={templateId} patient={patient} content={content} diagnoses={diagnoses}
            readOnly={!editable} errors={errorSet}
            comments={note.feedback.filter((item) => item.sectionId)}
            onField={setField} onDiagnoses={(d) => { markDirty(); setDiagnoses(d); }}
            onFill={(sectionId) => {
              const template = TEMPLATES[templateId as keyof typeof TEMPLATES];
              const draft = prefillFromPatient(templateId, patient, template);
              const section = template?.sections.find((item) => item.id === sectionId);
              if (!section) return;
              markDirty();
              setContent((prev) => {
                const next = { ...prev };
                for (const field of section.fields) {
                  if (!next[field.id]?.trim() && draft[field.id]) next[field.id] = draft[field.id];
                }
                return next;
              });
            }}
          />

          <Alert severity="info" sx={{ mt: 2 }}>
            <Typography variant="body2" sx={{ fontWeight: 700 }}>ICD-10 and coverage (teaching)</Typography>
            <Typography variant="body2">
              Diagnosis codes on this note support billing and coverage decisions. Payers use ICD-10
              (with CPT when billed) to decide what gets paid — for example, an encounter coded as
              E11.65 tells insurance why the visit is covered. This product does not submit real claims.
            </Typography>
            {(patient.insurance?.payer || patient.insurance?.memberId) && (
              <Typography variant="body2" sx={{ mt: 0.75 }}>
                Chart payer on file:{" "}
                {[patient.insurance.payer, patient.insurance.memberId && `member ${patient.insurance.memberId}`]
                  .filter(Boolean)
                  .join(" · ")}
              </Typography>
            )}
            {diagnoses[0] && (
              <Typography variant="body2" sx={{ mt: 0.5 }}>
                Primary diagnosis on this note: <b>{diagnoses[0].code}</b> {diagnoses[0].label}
              </Typography>
            )}
          </Alert>

          <TextField
            select label="Billing codes (CPT)" value={cptCodes.map((item) => item.code)}
            disabled={!editable} sx={{ mt: 2 }}
            helperText="Office and related E/M codes only. This chart does not calculate charges."
            slotProps={{ select: { multiple: true } }}
            onChange={(event) => {
              const selected = event.target.value as unknown as string[];
              markDirty();
              setCptCodes(selected.flatMap((code) => {
                const option = cptOptions.find((item) => item.code === code);
                const previous = cptCodes.find((item) => item.code === code);
                if (!option) return previous ? [previous] : [];
                return [{ ...option, diagnosisCodes: previous?.diagnosisCodes ?? [] }];
              }));
            }}
          >
            {cptCodes.filter((item) => !cptOptions.some((option) => option.code === item.code)).map((item) => (
              <MenuItem key={item.code} value={item.code} disabled>{item.code} {item.label} (legacy)</MenuItem>
            ))}
            {cptOptions.map((item) => <MenuItem key={item.code} value={item.code}>{item.code} {item.label}</MenuItem>)}
          </TextField>
          <Stack spacing={1} sx={{ mt: 1.5 }}>
            {cptCodes.map((cpt) => (
              <Box key={cpt.code}>
                <Autocomplete
                  multiple
                  size="small"
                  options={diagnoses}
                  value={diagnoses.filter((diagnosis) => cpt.diagnosisCodes.includes(diagnosis.code))}
                  getOptionLabel={(option) => `${option.code} ${option.label}`}
                  isOptionEqualToValue={(option, value) => option.code === value.code}
                  onChange={(_, selected) => {
                    markDirty();
                    setCptCodes((current) => current.map((item) => item.code === cpt.code
                      ? { ...item, diagnosisCodes: selected.map((diagnosis) => diagnosis.code) }
                      : item));
                  }}
                  renderInput={(params) => <TextField {...params} label={`Diagnoses for ${cpt.code}`} />}
                />
                {cpt.diagnosisCodes.length === 0 && (
                  <Typography variant="caption" color="text.secondary">No linked diagnosis (optional).</Typography>
                )}
              </Box>
            ))}
          </Stack>

          {!isSimulation && (note.status === "signed" || note.status === "cosigned" || (note.status === "returned" && note.bodyLocked)) && (
            <>
              <Divider sx={{ my: 3 }} />
              <Addenda
                items={note.addenda}
                onAdd={note.authorId === user.id ? async (body) => hydrate(await addAddendum(note.id, body, activeRole)) : undefined}
              />
            </>
          )}
        </Paper>

        {/* Side panel */}
        <Stack spacing={2} sx={{ position: { lg: "sticky" }, top: { lg: 88 } }}>
          <Paper sx={{ p: 2.5 }}>
            <Typography component="h2" variant="subtitle1" sx={{ mb: 1 }}>{isSimulation ? "Simulation note" : isAssessment ? "Submission" : "Practice note"}</Typography>
            <NoteProgress note={note} />
            {activeRole !== "student" && <CourseRubricPanel guide={guide.data} fileName={guide.data?.file_name} />}
            {activeRole === "student" && note.status === "cosigned" && (
              <Box sx={{ mt: 2 }}>
                <AnswerKeyPanel role={activeRole} patientId={patient.id} />
              </Box>
            )}

            {editable && (
              <Stack spacing={1.5} sx={{ mt: 2 }}>
                {isAssessment && (
                  <TextField
                    select id="route-select" label="Send for co-signature to" value={routedToId}
                    error={showErrors && needsRoute} helperText={showErrors && needsRoute ? "Choose your reviewing instructor." : undefined}
                    onChange={(e) => { markDirty(); setRoutedToId(e.target.value); }}
                  >
                    {instructors.map((i) => <MenuItem key={i.id} value={i.id}>{i.fullName}</MenuItem>)}
                  </TextField>
                )}
                <Button variant="contained" size="large" onClick={trySign}>
                  {isSimulation ? "Sign and close note" : !isAssessment ? "Sign note" : note.status === "returned" ? "Sign and resubmit" : "Submit for signature"}
                </Button>
                <Typography variant="caption" color="text.secondary" role="status" aria-live="polite">
                  {saveState === "saving" && "Saving…"}
                  {saveState === "saved" && savedAt && `Draft saved at ${formatTime(savedAt)}`}
                  {saveState === "idle" && (pending ? "Unsaved changes" : "Drafts save automatically")}
                  {saveState === "error" && "Not saved. See the message above."}
                </Typography>
              </Stack>
            )}
            {isSimulation && (
              <Typography variant="caption" color="text.secondary" sx={{ display: "block", mt: 1.5 }}>
                Signing closes this note. A later clarification is a separate note and does not reopen it.
              </Typography>
            )}
            {isAssessment && (
              <Typography variant="caption" color="text.secondary" sx={{ display: "block", mt: 1.5 }}>
                You sign as the author. The note isn't final until an instructor co-signs. Prescribing is simulated.
              </Typography>
            )}
          </Paper>

          <Paper sx={{ overflow: "hidden" }}>
            <Typography component="h2" variant="subtitle1" sx={{ px: 2, pt: 1.5 }}>Chart</Typography>
            <ChartReference patient={patient} />
          </Paper>
        </Stack>
      </Box>

      <Dialog open={confirmOpen} onClose={() => setConfirmOpen(false)}>
        <DialogTitle>{isSimulation ? "Close this note?" : isAssessment ? "Submit this note for signature?" : "Sign this note?"}</DialogTitle>
        <DialogContent>
          <DialogContentText>
            {isSimulation
              ? "The visit note locks. Anyone on the team can open a new clarification note afterward."
              : isAssessment
              ? `It goes to ${reviewer?.fullName ?? "your instructor"} for review. You won't be able to edit it unless it's returned.`
              : "Signed notes are locked. You can still add an addendum."}
          </DialogContentText>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setConfirmOpen(false)}>Keep editing</Button>
          <Button variant="contained" onClick={doSign}>{isSimulation ? "Sign and close" : isAssessment ? "Submit for signature" : "Sign note"}</Button>
        </DialogActions>
      </Dialog>
    </Stack>
  );
}
