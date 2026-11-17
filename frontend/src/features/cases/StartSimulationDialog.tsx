import { useState } from "react";
import { Alert, Button, Dialog, DialogActions, DialogContent, DialogTitle, MenuItem, Stack, TextField, Typography } from "@mui/material";
import type { AuthoredCase, Patient, User } from "../../types";
import { startSimulation } from "../../api/cases";
import { listRoster } from "../../api/roster";
import { useSession } from "../auth/useSession";
import { useAsync } from "../../utils/useAsync";

interface Props {
  item: AuthoredCase;
  onClose: () => void;
  onStarted: (patient: Patient) => void;
}

export default function StartSimulationDialog({ item, onClose, onStarted }: Props) {
  const { activeRole, courseId } = useSession();
  const roster = useAsync(() => listRoster(courseId), [courseId]);
  const students = (roster.data ?? []).filter((student) => student.rosterStatus !== "inactive");
  const [nurseId, setNurseId] = useState("");
  const [pharmacistId, setPharmacistId] = useState("");
  const [providerId, setProviderId] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const submit = async () => {
    if (!nurseId || (!pharmacistId && !providerId)) {
      setError("Choose a nurse and at least one of pharmacist or provider.");
      return;
    }
    setBusy(true);
    setError("");
    try {
      const chart = await startSimulation(activeRole, courseId, item.id, {
        nurseId,
        pharmacistId: pharmacistId || undefined,
        providerId: providerId || undefined,
      });
      onStarted(chart);
    } catch (e) {
      setError((e as Error).message);
      setBusy(false);
    }
  };

  const field = (label: string, value: string, set: (next: string) => void, required = false) => (
    <TextField select label={label} value={value} required={required} onChange={(event) => set(event.target.value)} disabled={roster.loading}>
      <MenuItem value="">{required ? "Choose a student" : "None"}</MenuItem>
      {students.map((student: User) => (
        <MenuItem key={student.id} value={student.id}>{student.fullName}</MenuItem>
      ))}
    </TextField>
  );

  return (
    <Dialog open onClose={onClose} fullWidth maxWidth="sm">
      <DialogTitle>Start simulation</DialogTitle>
      <DialogContent>
        <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
          One shared chart for {item.lastName}, {item.firstName}. Each person signs in with their own account. Graded copies stay private.
        </Typography>
        <Stack spacing={2}>
          {error && <Alert severity="error">{error}</Alert>}
          {field("Nurse", nurseId, setNurseId, true)}
          {field("Pharmacist", pharmacistId, setPharmacistId)}
          {field("Provider", providerId, setProviderId)}
        </Stack>
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose}>Cancel</Button>
        <Button variant="contained" disabled={busy} onClick={submit}>{busy ? "Starting..." : "Start"}</Button>
      </DialogActions>
    </Dialog>
  );
}
