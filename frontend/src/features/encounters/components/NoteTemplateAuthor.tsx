import { useState } from "react";
import { Alert, Button, Checkbox, FormControlLabel, MenuItem, Paper, Stack, TextField, Typography } from "@mui/material";
import { createNoteTemplate, listNoteTemplates } from "../../../api/templates";
import type { Discipline, Role } from "../../../types";
import { useAsync } from "../../../utils/useAsync";

const DISCIPLINES: { value: Discipline; label: string }[] = [
  { value: "pharmacy", label: "Pharmacy" },
  { value: "physical_therapy", label: "Physical therapy" },
  { value: "occupational_therapy", label: "Occupational therapy" },
  { value: "speech_language_pathology", label: "Speech-language pathology" },
  { value: "nursing", label: "Nursing" },
];

export default function NoteTemplateAuthor({ role, courseId }: { role: Role; courseId?: string }) {
  const saved = useAsync(() => listNoteTemplates(role, courseId), [role, courseId]);
  const [name, setName] = useState("");
  const [discipline, setDiscipline] = useState<Discipline>("pharmacy");
  const [sectionTitle, setSectionTitle] = useState("Note");
  const [fieldLabel, setFieldLabel] = useState("");
  const [sensitive, setSensitive] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  const save = async () => {
    setError("");
    setMessage("");
    try {
      await createNoteTemplate(role, {
        name: name.trim(),
        discipline,
        courseId,
        sensitive,
        sections: [{
          id: "N",
          title: sectionTitle.trim() || "Note",
          fields: [{ id: "body", label: fieldLabel.trim() || "Note", kind: "textarea" }],
        }],
      });
      setName("");
      setFieldLabel("");
      setSensitive(false);
      setMessage(courseId ? "Saved for this class." : "Saved as a shared template.");
      saved.reload();
    } catch (e) {
      setError((e as Error).message);
    }
  };

  const rows = (saved.data ?? []).filter((row) => (courseId ? row.scope === "course" : row.scope === "shared"));

  return (
    <Paper sx={{ p: 2.5 }}>
      <Typography component="h2" variant="h6">{courseId ? "Templates for this class" : "Shared note templates"}</Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5, mb: 1.5 }}>
        Built-in templates stay as they are. A sensitive template hides its notes from students.
      </Typography>
      {message && <Alert severity="success" sx={{ mb: 1.5 }} onClose={() => setMessage("")}>{message}</Alert>}
      {error && <Alert severity="error" sx={{ mb: 1.5 }} onClose={() => setError("")}>{error}</Alert>}
      <Stack spacing={1.5}>
        <TextField label="Template name" value={name} onChange={(e) => setName(e.target.value)} />
        <TextField select label="Discipline" value={discipline} onChange={(e) => setDiscipline(e.target.value as Discipline)}>
          {DISCIPLINES.map((item) => <MenuItem key={item.value} value={item.value}>{item.label}</MenuItem>)}
        </TextField>
        <TextField label="Section title" value={sectionTitle} onChange={(e) => setSectionTitle(e.target.value)} />
        <TextField label="Field label" value={fieldLabel} onChange={(e) => setFieldLabel(e.target.value)} />
        <FormControlLabel
          control={<Checkbox checked={sensitive} onChange={(e) => setSensitive(e.target.checked)} />}
          label="Sensitive. Students cannot open notes that use this template."
        />
        <Button variant="contained" disabled={!name.trim()} onClick={save}>Save template</Button>
      </Stack>
      {rows.length > 0 && (
        <Stack component="ul" sx={{ mt: 2, mb: 0, pl: 2.5 }}>
          {rows.map((row) => (
            <Typography key={row.id} component="li" variant="body2">
              {row.name}{row.sensitive ? " (sensitive)" : ""}
            </Typography>
          ))}
        </Stack>
      )}
    </Paper>
  );
}
