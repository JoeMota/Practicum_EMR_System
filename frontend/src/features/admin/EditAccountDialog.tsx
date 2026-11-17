import { useState, type FormEvent } from "react";
import { Box, Button, Dialog, DialogActions, DialogContent, DialogTitle, Stack, TextField } from "@mui/material";
import type { User } from "../../types";
import { updateAccount } from "../../api/users";

interface EditAccountDialogProps {
  person?: User;
  requireStudentId: boolean;
  onClose: () => void;
  onSaved: (person: User) => void;
}

export default function EditAccountDialog({ person, requireStudentId, onClose, onSaved }: EditAccountDialogProps) {
  const [fullName, setFullName] = useState(person?.fullName ?? "");
  const [email, setEmail] = useState(person?.email ?? "");
  const [universityId, setUniversityId] = useState(person?.universityId ?? "");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const save = async (event: FormEvent) => {
    event.preventDefault();
    if (!person) return;
    const id = universityId.trim();
    if (!fullName.trim()) {
      setError("Name is required.");
      return;
    }
    if (!email.trim()) {
      setError("Email is required.");
      return;
    }
    if (requireStudentId && !/^800\d{6}$/.test(id)) {
      setError("Students need a 9-digit 800 number.");
      return;
    }
    setBusy(true);
    setError("");
    try {
      onSaved(await updateAccount(person.id, { fullName: fullName.trim(), email: email.trim(), universityId: id }));
      onClose();
    } catch (e) {
      setError((e as Error).message);
      setBusy(false);
    }
  };

  return (
    <Dialog open={Boolean(person)} onClose={onClose} fullWidth maxWidth="xs">
      <Box component="form" onSubmit={save}>
      <DialogTitle>Edit account</DialogTitle>
      <DialogContent>
        <Stack spacing={1.5} sx={{ mt: 0.5 }}>
          <TextField size="small" label="Full name" value={fullName} onChange={(event) => setFullName(event.target.value)} />
          <TextField size="small" label="Email" value={email} onChange={(event) => setEmail(event.target.value)} />
          <TextField
            size="small" label="800 number" value={universityId} onChange={(event) => setUniversityId(event.target.value)}
            helperText={error || (requireStudentId ? "Required for a student account." : "Leave blank for an instructor.")}
            error={Boolean(error)}
          />
        </Stack>
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose}>Cancel</Button>
        <Button type="submit" variant="contained" disabled={busy}>{busy ? "Saving..." : "Save"}</Button>
      </DialogActions>
      </Box>
    </Dialog>
  );
}
