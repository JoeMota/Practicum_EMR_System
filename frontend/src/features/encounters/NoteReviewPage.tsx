import { useState } from "react";
import {
  Alert, Box, Breadcrumbs, Button, Divider, LinearProgress, Link, Paper, Stack, TextField, Typography,
} from "@mui/material";
import { Link as RouterLink, useNavigate, useParams } from "react-router-dom";
import { commentOnNote, cosignNote, getNote, instructorEditNote, returnNote } from "../../api/notes";
import { getPatient } from "../../api/patients";
import { getChartGradingGuide, releaseChartAnswerKey } from "../../api/cases";
import { useSession } from "../auth/useSession";
import { useAsync } from "../../utils/useAsync";
import { formatDateTime } from "../../utils/format";
import { disciplineLabel } from "../../utils/labels";
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
import { templateName } from "./noteTemplates";
import ScoreForm from "./components/ScoreForm";
import TriggersPanel from "./components/TriggersPanel";
import type { IcdCode } from "../../types";

export default function NoteReviewPage() {
  const { noteId = "" } = useParams();
  const navigate = useNavigate();
  const { activeRole } = useSession();
  const [comment, setComment] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [editing, setEditing] = useState(false);
  const [draftContent, setDraftContent] = useState<Record<string, string>>({});
  const [draftDiagnoses, setDraftDiagnoses] = useState<IcdCode[]>([]);
  const [releaseBusy, setReleaseBusy] = useState(false);
  const [releaseNote, setReleaseNote] = useState("");

  const load = useAsync(async () => {
    const note = await getNote(activeRole, noteId);
    const patient = await getPatient(activeRole, note.patientId);
    return { note, patient };
  }, [noteId, activeRole]);
  const guide = useAsync(async () => {
    const id = load.data?.patient.id;
    if (!id) return { criteria: [], source: "course" as const };
    return getChartGradingGuide(activeRole, id);
  }, [activeRole, load.data?.patient.id]);

  if (load.error) return <PageError error={load.error} />;
  if (!load.data) return <LinearProgress aria-label="Loading note" />;
  const { note, patient } = load.data;
  const pending = note.status === "pending_review";

  const act = async (kind: "cosign" | "return") => {
    if (kind === "return" && !comment.trim()) {
      setError("Tell the student what to revise before returning the note.");
      document.getElementById("review-comment")?.focus();
      return;
    }
    setBusy(true);
    setError("");
    try {
      const updated = kind === "cosign"
        ? await cosignNote(activeRole, note.id, comment)
        : await returnNote(activeRole, note.id, comment);
      load.setData({ note: updated, patient });
      setComment("");
      const flash = kind === "cosign"
        ? `Co-signed ${note.authorName}'s note.`
        : `Returned ${note.authorName}'s note for revision.`;
      navigate("/review", { replace: true, state: { flash } });
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <Stack spacing={2}>
      <Breadcrumbs aria-label="Breadcrumb">
        <Link component={RouterLink} to="/review" underline="hover">Review queue</Link>
        <Typography color="text.primary">{note.authorName}</Typography>
      </Breadcrumbs>

      <PatientBanner patient={patient} ownerName={patient.ownerName} compact />

      <Box
        sx={{
          display: "grid",
          gap: 2.5,
          alignItems: "start",
          gridTemplateColumns: { xs: "1fr", md: "minmax(0, 1fr) 300px", lg: "minmax(0, 1fr) minmax(240px, 320px) 320px" },
        }}
      >
        <Paper component="article" aria-label="Student note" sx={{ p: { xs: 2, md: 3 } }}>
          <Box sx={{ display: "flex", alignItems: "center", gap: 1.5, flexWrap: "wrap", mb: 2.5 }}>
            <Box sx={{ flex: 1 }}>
              <Typography component="h2" variant="h5">{templateName(note.templateId)}</Typography>
              <Typography variant="body2" color="text.secondary">
                {note.authorName}, {disciplineLabel[note.authorDiscipline]} student
                {note.signedAt ? `. Signed ${formatDateTime(note.signedAt)}` : ""}
              </Typography>
            </Box>
            <NoteStatusChip status={note.status} />
            {pending && !note.bodyLocked && (
              <Button size="small" variant="outlined" onClick={() => {
                if (editing) {
                  setEditing(false);
                  return;
                }
                setDraftContent(note.content);
                setDraftDiagnoses(note.diagnoses);
                setEditing(true);
              }}>{editing ? "Cancel edit" : "Edit note"}</Button>
            )}
          </Box>
          <NoteFields
            templateId={note.templateId} patient={patient}
            content={editing ? draftContent : note.content}
            diagnoses={editing ? draftDiagnoses : note.diagnoses}
            readOnly={!editing}
            comments={note.feedback}
            onField={editing ? (id, next) => setDraftContent((current) => ({
              ...current,
              [id]: typeof next === "function" ? next(current[id] ?? "") : next,
            })) : undefined}
            onDiagnoses={editing ? setDraftDiagnoses : undefined}
            onComment={pending && !editing ? async (sectionId, body) => {
              const updated = await commentOnNote(activeRole, note.id, { sectionId, body });
              load.setData({ note: updated, patient });
            } : undefined}
          />
          {editing && (
            <Button sx={{ mt: 2 }} variant="contained" disabled={busy} onClick={async () => {
              setBusy(true);
              setError("");
              try {
                const updated = await instructorEditNote(activeRole, note.id, { content: draftContent, diagnoses: draftDiagnoses });
                load.setData({ note: updated, patient });
                setEditing(false);
              } catch (e) {
                setError((e as Error).message);
              } finally {
                setBusy(false);
              }
            }}>Save instructor edit</Button>
          )}
          {note.addenda.length > 0 && (<><Divider sx={{ my: 3 }} /><Addenda items={note.addenda} /></>)}
        </Paper>

        <Paper sx={{ p: 2.5, position: { lg: "sticky" }, top: { lg: 88 }, gridColumn: { md: "2", lg: "2" } }}>
          <AnswerKeyPanel role={activeRole} patientId={patient.id} />
          {note.status === "cosigned" && (
            <Stack spacing={1} sx={{ mt: 2 }}>
              {releaseNote && <Alert severity="success">{releaseNote}</Alert>}
              <Button
                variant="outlined"
                size="small"
                disabled={releaseBusy}
                onClick={async () => {
                  setReleaseBusy(true);
                  setReleaseNote("");
                  setError("");
                  try {
                    await releaseChartAnswerKey(activeRole, patient.id);
                    setReleaseNote("Answer key released. The student can read it on this chart.");
                  } catch (e) {
                    setError((e as Error).message);
                  } finally {
                    setReleaseBusy(false);
                  }
                }}
              >
                Release answer key to student
              </Button>
              <Typography variant="caption" color="text.secondary">
                Students see the key only after co-sign and this release.
              </Typography>
            </Stack>
          )}
          {note.status !== "cosigned" && <TriggersPanel role={activeRole} patientId={patient.id} />}
        </Paper>

        <Stack spacing={2} sx={{ position: { lg: "sticky" }, top: { lg: 88 }, gridColumn: { xs: "1", md: "1 / -1", lg: "3" } }}>
          <Paper sx={{ p: 2.5 }}>
            <Typography component="h2" variant="subtitle1" sx={{ mb: 1 }}>Your review</Typography>
            <NoteProgress note={note} />

            <CourseRubricPanel guide={guide.data} fileName={guide.data?.file_name} />

            {note.feedback.length > 0 && (
              <Box sx={{ mt: 2 }}><FeedbackThread items={note.feedback} /></Box>
            )}

            {pending && (
              <Stack spacing={1.5} sx={{ mt: 2 }}>
                {error && <Alert severity="error">{error}</Alert>}
                <TextField
                  id="review-comment" label="Feedback to the student" multiline minRows={4} value={comment}
                  onChange={(e) => setComment(e.target.value)}
                  helperText="Required to return the note. Optional when co-signing. You leave comments — the student's wording stays theirs."
                />
                <Button variant="contained" size="large" disabled={busy} onClick={() => act("cosign")}>
                  Co-sign and accept
                </Button>
                <Button variant="outlined" color="error" disabled={busy} onClick={() => act("return")}>
                  Return for revision
                </Button>
                <Typography variant="caption" color="text.secondary">
                  Return is the usual path and reopens the note. Co-sign locks the wording. Later corrections are addenda.
                </Typography>
              </Stack>
            )}
            {(pending || note.status === "cosigned") && (
              <ScoreForm
                key={(guide.data?.criteria ?? []).map((item) => item.id).join()}
                role={activeRole}
                note={note}
                guide={guide.data}
                onSaved={(updated) => load.setData({ note: updated, patient })}
              />
            )}
          </Paper>

          <Paper sx={{ overflow: "hidden" }}>
            <Typography component="h2" variant="subtitle1" sx={{ px: 2, pt: 1.5 }}>Chart at time of review</Typography>
            <ChartReference patient={patient} />
          </Paper>
        </Stack>
      </Box>
    </Stack>
  );
}
