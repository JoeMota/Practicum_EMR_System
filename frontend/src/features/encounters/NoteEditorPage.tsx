import { useCallback, useEffect, useRef, useState } from "react";
import {
  Alert, Box, Breadcrumbs, Button, Dialog, DialogActions, DialogContent, DialogContentText, DialogTitle,
  Divider, LinearProgress, Link, MenuItem, Paper, Stack, TextField, Typography,
} from "@mui/material";
import { Link as RouterLink, useNavigate, useParams } from "react-router-dom";
import type { ClinicalNote, IcdCode, NoteTemplateId, Patient, User } from "../../types";
import { getPatient } from "../../api/patients";
import { addAddendum, createDraft, getNote, listNotesForPatient, saveDraft, signNote } from "../../api/notes";
import { listInstructors } from "../../api/courses";
import { useSession } from "../auth/AuthContext";
import { formatTime } from "../../utils/format";
import NoteStatusChip from "../../components/NoteStatusChip";
import PageError from "../../components/PageError";
import PatientBanner from "../patients/components/PatientBanner";
import ChartReference from "../patients/components/ChartReference";
import NoteFields from "./components/NoteFields";
import NoteProgress from "./components/NoteProgress";
import FeedbackThread from "./components/FeedbackThread";
import Addenda from "./components/Addenda";
import { TEMPLATES, defaultTemplateFor, diagnosesFromPatient, missingRequired, prefillFromPatient, templatesFor } from "./noteTemplates";

type SaveState = "idle" | "saving" | "saved" | "error";

/** Survives StrictMode remount so /notes/new doesn't POST two drafts. */
const creatingDraftKeys = new Set<string>();

export default function NoteEditorPage() {
  const { patientId = "", noteId = "new" } = useParams();
  const navigate = useNavigate();
  const { user, activeRole, discipline, courseId } = useSession();

  const [patient, setPatient] = useState<Patient>();
  const [note, setNote] = useState<ClinicalNote>();
  const [instructors, setInstructors] = useState<User[]>([]);
  const [loadError, setLoadError] = useState<Error>();

  const [templateId, setTemplateId] = useState<NoteTemplateId>(defaultTemplateFor(discipline));
  const [content, setContent] = useState<Record<string, string>>({});
  const [diagnoses, setDiagnoses] = useState<IcdCode[]>([]);
  const [routedToId, setRoutedToId] = useState("");

  const [saveState, setSaveState] = useState<SaveState>("idle");
  const [savedAt, setSavedAt] = useState<string>();
  const [error, setError] = useState("");
  const [showErrors, setShowErrors] = useState(false);
  const [confirmOpen, setConfirmOpen] = useState(false);

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
          const key = `${user.id}:${patientId}`;
          if (creatingDraftKeys.has(key)) return;
          creatingDraftKeys.add(key);
          try {
            const existing = (await listNotesForPatient(activeRole, patientId)).find(
              (n) => n.authorId === user.id && (n.status === "draft" || n.status === "returned"),
            );
            const n = existing ?? (await createDraft(discipline ?? "pharmacy", p, defaultTemplateFor(discipline), activeRole));
            if (!alive) return;
            navigate(`/patients/${patientId}/notes/${n.id}`, { replace: true });
          } finally {
            creatingDraftKeys.delete(key);
          }
          return;
        }
        const n = await getNote(activeRole, noteId);
        if (!alive) return;
        hydrate(n, people);
      } catch (e) {
        if (alive) setLoadError(e as Error);
      }
    })();
    return () => { alive = false; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [patientId, noteId]);

  const version = useRef(0);
  const hydrate = (n: ClinicalNote, people: User[] = instructors) => {
    setNote(n);
    version.current = n.version;
    setTemplateId(n.templateId);
    setContent(n.content);
    setDiagnoses(n.diagnoses);
    setRoutedToId(n.routedToId ?? (n.mode === "assessment" ? people[0]?.id ?? "" : ""));
  };

  const latest = useRef({ templateId, content, diagnoses, routedToId });
  latest.current = { templateId, content, diagnoses, routedToId };
  const changeSeq = useRef(0);
  const savedSeq = useRef(0);
  const saving = useRef(false);

  const editable = Boolean(note && note.authorId === user.id && (note.status === "draft" || note.status === "returned"));

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
    setSaveState((s) => (s === "error" ? s : "idle"));
  };

  useEffect(() => {
    if (!editable || changeSeq.current === savedSeq.current) return;
    const t = setTimeout(save, 1200);
    return () => clearTimeout(t);
  }, [content, diagnoses, templateId, routedToId, editable, save]);

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

  const missing = missingRequired(templateId, content, diagnoses.length);
  const needsRoute = note?.mode === "assessment" && !routedToId;

  const trySign = () => {
    setShowErrors(true);
    if (missing.length || needsRoute) {
      const first = missing[0] ? `field-${missing[0]}` : "route-select";
      document.getElementById(first)?.focus();
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
  const reviewer = instructors.find((i) => i.id === (note.routedToId ?? routedToId));
  const errorSet = showErrors ? new Set(missing) : undefined;
  const choices = templatesFor(discipline);

  return (
    <Stack spacing={2}>
      <Breadcrumbs aria-label="Breadcrumb">
        <Link component={RouterLink} to="/patients" underline="hover">My patients</Link>
        <Link component={RouterLink} to={`/patients/${patient.id}`} underline="hover">{patient.lastName}, {patient.firstName}</Link>
        <Typography color="text.primary">{TEMPLATES[templateId].name}</Typography>
      </Breadcrumbs>

      <PatientBanner patient={patient} compact />

      <Box sx={{ display: "grid", gap: 2.5, gridTemplateColumns: { xs: "1fr", lg: "1fr 340px" }, alignItems: "start" }}>
        {/* Editor */}
        <Paper component="article" aria-label="Note" sx={{ p: { xs: 2, md: 3 } }}>
          <Box sx={{ display: "flex", alignItems: "center", gap: 1.5, flexWrap: "wrap", mb: 2.5 }}>
            <Box sx={{ flex: 1, minWidth: 220 }}>
              <Typography component="h2" variant="h5">{TEMPLATES[templateId].name}</Typography>
              <Typography variant="body2" color="text.secondary">
                {patient.encounter.type}, {note.authorName}
              </Typography>
            </Box>
            <NoteStatusChip status={note.status} />
            {editable && note.status === "draft" && choices.length > 1 && (
              <TextField
                select size="small" label="Template" value={templateId} sx={{ minWidth: 240 }}
                onChange={(e) => {
                  const next = e.target.value as NoteTemplateId;
                  markDirty();
                  setTemplateId(next);
                  // Keep student edits; only fill empty fields for the new template.
                  const seeded = prefillFromPatient(next, patient);
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
              <FeedbackThread items={note.feedback} />
            </Alert>
          )}
          {note.status === "pending_review" && (
            <Alert severity="info" sx={{ mb: 2.5 }}>
              Submitted to {reviewer?.fullName ?? "your instructor"}. You can edit again only if it's returned.
            </Alert>
          )}
          {note.status === "cosigned" && note.feedback.length > 0 && (
            <Alert severity="success" sx={{ mb: 2.5 }}><FeedbackThread items={note.feedback} /></Alert>
          )}
          {editable && note.status === "draft" && (
            content.reason || content.cc || content.hpi || content.subjective || content.objective || content.exam || content.measures || content.history || diagnoses.length > 0
          ) && (
            <Alert severity="info" icon={false} sx={{ mb: 2.5 }}>
              We prefilled what we could from the chart (complaint, vitals/labs, history, and any coded diagnoses). Review and complete the rest before you sign.
            </Alert>
          )}
          {error && <Alert severity="error" onClose={() => setError("")} sx={{ mb: 2.5 }}>{error}</Alert>}

          <NoteFields
            templateId={templateId} patient={patient} content={content} diagnoses={diagnoses}
            readOnly={!editable} errors={errorSet}
            onField={setField} onDiagnoses={(d) => { markDirty(); setDiagnoses(d); }}
          />

          {(note.status === "signed" || note.status === "cosigned") && (
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
            <Typography component="h2" variant="subtitle1" sx={{ mb: 1 }}>{isAssessment ? "Submission" : "Practice note"}</Typography>
            <NoteProgress note={note} />

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
                {showErrors && missing.length > 0 && (
                  <Alert severity="warning">Complete {missing.length} required {missing.length === 1 ? "field" : "fields"} before signing.</Alert>
                )}
                <Button variant="contained" size="large" onClick={trySign}>
                  {!isAssessment ? "Sign note" : note.status === "returned" ? "Sign and resubmit" : "Submit for signature"}
                </Button>
                <Typography variant="caption" color="text.secondary" role="status" aria-live="polite">
                  {saveState === "saving" && "Saving…"}
                  {saveState === "saved" && savedAt && `Draft saved at ${formatTime(savedAt)}`}
                  {saveState === "idle" && (changeSeq.current !== savedSeq.current ? "Unsaved changes" : "Drafts save automatically")}
                  {saveState === "error" && "Not saved. See the message above."}
                </Typography>
              </Stack>
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
        <DialogTitle>{isAssessment ? "Submit this note for signature?" : "Sign this note?"}</DialogTitle>
        <DialogContent>
          <DialogContentText>
            {isAssessment
              ? `It goes to ${reviewer?.fullName ?? "your instructor"} for review. You won't be able to edit it unless it's returned.`
              : "Signed notes are locked. You can still add an addendum."}
          </DialogContentText>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setConfirmOpen(false)}>Keep editing</Button>
          <Button variant="contained" onClick={doSign}>{isAssessment ? "Submit for signature" : "Sign note"}</Button>
        </DialogActions>
      </Dialog>
    </Stack>
  );
}
