import { useState } from "react";
import {
  Alert, Box, Breadcrumbs, Button, Divider, LinearProgress, Link, Paper, Stack, TextField, Typography,
} from "@mui/material";
import DescriptionOutlined from "@mui/icons-material/DescriptionOutlined";
import { Link as RouterLink, useParams } from "react-router-dom";
import { cosignNote, getNote, returnNote } from "../../api/notes";
import { getPatient } from "../../api/patients";
import { getCourse } from "../../api/courses";
import { useSession } from "../auth/AuthContext";
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
import { TEMPLATES } from "./noteTemplates";

export default function NoteReviewPage() {
  const { noteId = "" } = useParams();
  const { user, activeRole, courseId } = useSession();
  const [comment, setComment] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const load = useAsync(async () => {
    const note = await getNote(user, activeRole, noteId);
    const patient = await getPatient(user, activeRole, note.patientId);
    return { note, patient };
  }, [noteId, user.id, activeRole]);
  const course = useAsync(() => getCourse(courseId), [courseId]);

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
        ? await cosignNote(user, activeRole, note.id, comment)
        : await returnNote(user, activeRole, note.id, comment);
      load.setData({ note: updated, patient });
      setComment("");
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <Stack spacing={2}>
      <Breadcrumbs>
        <Link component={RouterLink} to="/review" underline="hover">Review queue</Link>
        <Typography color="text.primary">{note.authorName}</Typography>
      </Breadcrumbs>

      <PatientBanner patient={patient} ownerName={patient.ownerName} compact />

      <Box sx={{ display: "grid", gap: 2.5, gridTemplateColumns: { xs: "1fr", lg: "1fr 360px" }, alignItems: "start" }}>
        <Paper component="article" aria-label="Student note" sx={{ p: { xs: 2, md: 3 } }}>
          <Box sx={{ display: "flex", alignItems: "center", gap: 1.5, flexWrap: "wrap", mb: 2.5 }}>
            <Box sx={{ flex: 1 }}>
              <Typography component="h2" variant="h5">{TEMPLATES[note.templateId].name}</Typography>
              <Typography variant="body2" color="text.secondary">
                {note.authorName}, {disciplineLabel[note.authorDiscipline]} student
                {note.signedAt ? `. Signed ${formatDateTime(note.signedAt)}` : ""}
              </Typography>
            </Box>
            <NoteStatusChip status={note.status} />
          </Box>
          <NoteFields templateId={note.templateId} patient={patient} content={note.content} diagnoses={note.diagnoses} readOnly />
          {note.addenda.length > 0 && (<><Divider sx={{ my: 3 }} /><Addenda items={note.addenda} /></>)}
        </Paper>

        <Stack spacing={2} sx={{ position: { lg: "sticky" }, top: { lg: 88 } }}>
          <Paper sx={{ p: 2.5 }}>
            <Typography component="h2" variant="subtitle1" sx={{ mb: 1 }}>Your review</Typography>
            <NoteProgress note={note} />

            {course.data?.rubricFileName && (
              <Button
                startIcon={<DescriptionOutlined />}
                size="small"
                sx={{ mt: 1.5 }}
                href={`/rubrics/${course.data.rubricFileName.replace(/\.pdf$/i, ".html")}`}
                target="_blank"
                rel="noopener noreferrer"
              >
                Open rubric ({course.data.rubricFileName})
              </Button>
            )}

            {note.feedback.length > 0 && (
              <Box sx={{ mt: 2 }}><FeedbackThread items={note.feedback} /></Box>
            )}

            {pending && (
              <Stack spacing={1.5} sx={{ mt: 2 }}>
                {error && <Alert severity="error">{error}</Alert>}
                <TextField
                  id="review-comment" label="Feedback to the student" multiline minRows={4} value={comment}
                  onChange={(e) => setComment(e.target.value)}
                  helperText="Required to return the note. Optional when co-signing."
                />
                <Button variant="contained" size="large" disabled={busy} onClick={() => act("cosign")}>Co-sign note</Button>
                <Button variant="outlined" color="error" disabled={busy} onClick={() => act("return")}>Return for revision</Button>
              </Stack>
            )}

            <Alert severity="info" icon={false} sx={{ mt: 2 }}>
              Record the score in the course gradebook. Grades aren't stored in the EMR, so students never see them here (FERPA).
            </Alert>
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
