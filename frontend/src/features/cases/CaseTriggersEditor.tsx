import { useState } from "react";
import { Alert, Box, Button, IconButton, Stack, TextField, Typography } from "@mui/material";
import DeleteOutlined from "@mui/icons-material/DeleteOutlined";
import { putTriggers } from "../../api/cases";
import type { PlantedTrigger, Role } from "../../types";

export default function CaseTriggersEditor({ role, caseId, initial }: { role: Role; caseId: string; initial: PlantedTrigger[] }) {
  const [rows, setRows] = useState<PlantedTrigger[]>(initial.length ? initial : [{ finding: "", explanation: "" }]);
  const [error, setError] = useState("");
  const [saved, setSaved] = useState("");
  const [busy, setBusy] = useState(false);

  const update = (index: number, patch: Partial<PlantedTrigger>) => {
    setRows((current) => current.map((row, i) => (i === index ? { ...row, ...patch } : row)));
    setSaved("");
  };

  return (
    <Stack spacing={1.5}>
      <Typography component="h2" variant="h6">Planted triggers</Typography>
      <Typography variant="body2" color="text.secondary">
        Findings the grader should notice, such as a drug interaction or an abnormal lab. Students never see these. They disappear from the review screen after co-sign.
      </Typography>
      {rows.map((row, index) => (
        <Box key={index} sx={{ display: "grid", gap: 1, gridTemplateColumns: { xs: "1fr", sm: "1fr 1fr auto" }, alignItems: "start" }}>
          <TextField
            label={`Finding ${index + 1}`}
            value={row.finding}
            onChange={(e) => update(index, { finding: e.target.value })}
          />
          <TextField
            label="What the grader should use"
            value={row.explanation}
            onChange={(e) => update(index, { explanation: e.target.value })}
            multiline
            minRows={2}
          />
          <IconButton aria-label={`Remove trigger ${index + 1}`} onClick={() => setRows((current) => current.filter((_, i) => i !== index))}>
            <DeleteOutlined />
          </IconButton>
        </Box>
      ))}
      {error && <Alert severity="error">{error}</Alert>}
      {saved && <Alert severity="success">{saved}</Alert>}
      <Box sx={{ display: "flex", gap: 1 }}>
        <Button onClick={() => setRows((current) => [...current, { finding: "", explanation: "" }])}>Add trigger</Button>
        <Button variant="contained" disabled={busy} onClick={async () => {
          setBusy(true);
          setError("");
          setSaved("");
          try {
            const result = await putTriggers(role, caseId, rows);
            setRows(result.triggers.length ? result.triggers : [{ finding: "", explanation: "" }]);
            setSaved("Triggers saved. Students still cannot see them.");
          } catch (e) {
            setError((e as Error).message);
          } finally {
            setBusy(false);
          }
        }}>Save triggers</Button>
      </Box>
    </Stack>
  );
}
