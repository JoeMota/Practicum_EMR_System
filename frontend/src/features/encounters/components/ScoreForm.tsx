import { useState } from "react";
import { Button, Stack, TextField, Typography } from "@mui/material";
import type { ClinicalNote, GradingGuide, Role } from "../../../types";
import { saveScores } from "../../../api/notes";

export default function ScoreForm({
  role, note, guide, onSaved,
}: {
  role: Role;
  note: ClinicalNote;
  guide?: GradingGuide | null;
  onSaved: (note: ClinicalNote) => void;
}) {
  const criteria = guide?.criteria ?? [];
  const saved = note.rubricScores;
  const [rows, setRows] = useState(() => criteria.map((item) => {
    const existing = saved?.criteria.find((row) => row.id === item.id);
    return { id: item.id, label: item.label, max: item.max_points ?? null, score: existing?.score ?? "", feedback: existing?.feedback ?? "" };
  }));
  const [overall, setOverall] = useState(saved?.overall_feedback ?? "");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  if (criteria.length === 0) {
    return (
      <Typography variant="body2" color="text.secondary" sx={{ mt: 2 }}>
        Scores are stored on the note once a rubric has been converted. Upload a PDF or Word file with a heading or numbered line for each criterion.
      </Typography>
    );
  }

  const save = async () => {
    setBusy(true);
    setError("");
    try {
      const updated = await saveScores(role, note.id, {
        overallFeedback: overall,
        criteria: rows.map((row) => ({
          id: row.id,
          score: row.score === "" ? null : Number(row.score),
          feedback: row.feedback,
          maxPoints: row.max,
        })),
      });
      onSaved(updated);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <Stack spacing={1.5} sx={{ mt: 2 }}>
      <Typography variant="subtitle2">Rubric scores</Typography>
      {rows.map((row, index) => (
        <Stack key={row.id} spacing={1}>
          <Typography variant="body2" sx={{ fontWeight: 700 }}>
            {row.label}{row.max ? ` (up to ${row.max})` : ""}
          </Typography>
          <TextField
            size="small" type="number" label="Score" value={row.score}
            onChange={(event) => setRows((current) => current.map((item, i) => i === index ? { ...item, score: event.target.value } : item))}
          />
          <TextField
            size="small" label="Feedback" value={row.feedback} multiline minRows={2}
            onChange={(event) => setRows((current) => current.map((item, i) => i === index ? { ...item, feedback: event.target.value } : item))}
          />
        </Stack>
      ))}
      <TextField label="Overall feedback" value={overall} multiline minRows={3} onChange={(event) => setOverall(event.target.value)} />
      {error && <Typography variant="body2" color="error">{error}</Typography>}
      <Button variant="outlined" disabled={busy} onClick={save}>{busy ? "Saving scores..." : "Save scores"}</Button>
      <Typography variant="caption" color="text.secondary">Students do not see this rubric or these scores.</Typography>
    </Stack>
  );
}
