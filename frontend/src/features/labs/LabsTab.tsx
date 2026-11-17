import { useState } from "react";
import { Alert, Box, Button, Paper, Stack, Table, TableBody, TableCell, TableHead, TableRow, TextField, Typography } from "@mui/material";
import type { Patient } from "../../types";
import { addLab } from "../../api/chart";
import { useSession } from "../auth/useSession";
import { canEditSection } from "../chart/access";
import EmptyState from "../../components/EmptyState";
import { formatDate } from "../../utils/format";

export default function LabsTab({ patient, onChange }: { patient: Patient; onChange: (patient: Patient) => void }) {
  const { activeRole } = useSession();
  const editable = canEditSection(activeRole, patient, "labs");
  const [form, setForm] = useState({ name: "", value: "", unit: "", referenceRange: "", collectedAt: "" });
  const [error, setError] = useState("");

  const save = async () => {
    setError("");
    try {
      onChange(await addLab(activeRole, patient.id, { ...form, flag: undefined }));
      setForm({ name: "", value: "", unit: "", referenceRange: "", collectedAt: "" });
    } catch (e) {
      setError((e as Error).message);
    }
  };

  return (
    <Stack spacing={2}>
      {error && <Alert severity="error">{error}</Alert>}
      {editable && (
        <Paper sx={{ p: 2, borderRadius: "16px" }}>
          <Typography component="h2" variant="h6" sx={{ mb: 1.5 }}>Add a result</Typography>
          <Box sx={{ display: "grid", gap: 1.5, gridTemplateColumns: { xs: "1fr", sm: "1fr 1fr 1fr" } }}>
            <TextField label="Test" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
            <TextField label="Result" value={form.value} onChange={(e) => setForm({ ...form, value: e.target.value })} />
            <TextField label="Unit" value={form.unit} onChange={(e) => setForm({ ...form, unit: e.target.value })} />
            <TextField label="Reference range" value={form.referenceRange} onChange={(e) => setForm({ ...form, referenceRange: e.target.value })} />
            <TextField type="date" label="Collected" value={form.collectedAt} slotProps={{ inputLabel: { shrink: true } }} onChange={(e) => setForm({ ...form, collectedAt: e.target.value })} />
          </Box>
          <Button sx={{ mt: 1.5 }} variant="contained" onClick={save}>Add result</Button>
        </Paper>
      )}
      {patient.labs.length === 0 ? <EmptyState title="No lab results on file">Results added to this chart show up here with the date they were collected.</EmptyState> : (
        <Paper sx={{ borderRadius: "16px" }}>
          <Typography component="h2" variant="h6" sx={{ p: 2, pb: 1 }}>Lab results</Typography>
          <Box sx={{ overflowX: "auto" }}>
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell>Test</TableCell><TableCell align="right">Result</TableCell><TableCell>Units</TableCell><TableCell>Reference range</TableCell><TableCell>Collected</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {patient.labs.map((lab) => (
                  <TableRow key={lab.id}>
                    <TableCell>{lab.name}</TableCell>
                    <TableCell align="right">{lab.value}{lab.flag ? ` ${lab.flag}` : ""}</TableCell>
                    <TableCell>{lab.unit}</TableCell>
                    <TableCell>{lab.referenceRange}</TableCell>
                    <TableCell>{formatDate(lab.collectedAt)}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </Box>
        </Paper>
      )}
    </Stack>
  );
}
