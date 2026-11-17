import { useState } from "react";
import { Alert, Button, Dialog, DialogActions, DialogContent, DialogTitle, MenuItem, Stack, TextField } from "@mui/material";
import type { CareSetting, EncounterStatus, LifecycleStatus, Patient, PatientStatus } from "../../../types";

const LIFECYCLE: LifecycleStatus[] = ["Active", "Inactive", "Prospective", "Discharged from practice", "Archived", "Deceased"];
const ENCOUNTER: EncounterStatus[] = ["Scheduled", "Checked in", "Roomed", "In progress", "Checked out", "Closed"];
const SETTING: CareSetting[] = ["Outpatient", "Inpatient", "Emergency", "Discharged"];

interface Props {
  patient: Patient;
  open: boolean;
  onClose: () => void;
  onSave: (status: PatientStatus) => Promise<void>;
}

export default function StatusDialog({ patient, open, onClose, onSave }: Props) {
  const [s, setS] = useState<PatientStatus>(patient.status);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const save = async () => {
    setBusy(true);
    try {
      await onSave(s);
      onClose();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <Dialog open={open} onClose={onClose} fullWidth maxWidth="xs">
      <DialogTitle>Change patient status</DialogTitle>
      <DialogContent>
        <Stack spacing={2} sx={{ mt: 1 }}>
          {error && <Alert severity="error">{error}</Alert>}
          <TextField select label="Record" value={s.lifecycle} onChange={(e) => setS({ ...s, lifecycle: e.target.value as LifecycleStatus })}>
            {LIFECYCLE.map((v) => <MenuItem key={v} value={v}>{v}</MenuItem>)}
          </TextField>
          <TextField select label="Visit" value={s.encounter} onChange={(e) => setS({ ...s, encounter: e.target.value as EncounterStatus })}>
            {ENCOUNTER.map((v) => <MenuItem key={v} value={v}>{v}</MenuItem>)}
          </TextField>
          <TextField select label="Care setting" value={s.careSetting} onChange={(e) => setS({ ...s, careSetting: e.target.value as CareSetting })}>
            {SETTING.map((v) => <MenuItem key={v} value={v}>{v}</MenuItem>)}
          </TextField>
          <TextField label="Program status (optional)" value={s.program ?? ""} onChange={(e) => setS({ ...s, program: e.target.value || undefined })} />
        </Stack>
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose}>Cancel</Button>
        <Button variant="contained" onClick={save} disabled={busy}>Save status</Button>
      </DialogActions>
    </Dialog>
  );
}
