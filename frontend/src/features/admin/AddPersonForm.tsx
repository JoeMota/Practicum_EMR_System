import { useState, type FormEvent } from "react";
import { Button, Stack, TextField } from "@mui/material";
import type { Discipline, RosterRow } from "../../types";
import { validateRosterRow } from "./parseRoster";

interface AddPersonFormProps {
  role: "student" | "instructor";
  discipline: Discipline;
  onSubmit: (row: Pick<RosterRow, "fullName" | "email" | "universityId">) => Promise<boolean>;
}

export default function AddPersonForm({ role, onSubmit }: AddPersonFormProps) {
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [universityId, setUniversityId] = useState("");
  const [problems, setProblems] = useState<Partial<Record<"fullName" | "email" | "universityId", string>>>({});
  const [busy, setBusy] = useState(false);

  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const row = {
      fullName: fullName.trim(),
      email: email.trim().toLowerCase(),
      universityId: universityId.trim(),
    };
    const validated = validateRosterRow(row);
    if (validated.problem) {
      const field = validated.problem === "Missing name"
        ? "fullName"
        : validated.problem === "Email must be @miners.utep.edu or @utep.edu"
          ? "email"
          : "universityId";
      setProblems({ [field]: validated.problem });
      return;
    }

    setProblems({});
    setBusy(true);
    try {
      if (await onSubmit(row)) {
        setFullName("");
        setEmail("");
        setUniversityId("");
      }
    } finally {
      setBusy(false);
    }
  };

  return (
    <Stack component="form" spacing={1.5} onSubmit={submit} sx={{ mt: 1.5, maxWidth: 560 }}>
      <TextField
        size="small"
        label="Full name"
        value={fullName}
        onChange={(event) => setFullName(event.target.value)}
        error={Boolean(problems.fullName)}
        helperText={problems.fullName}
      />
      <TextField
        size="small"
        label="Email"
        value={email}
        onChange={(event) => setEmail(event.target.value)}
        error={Boolean(problems.email)}
        helperText={problems.email}
      />
      <TextField
        size="small"
        label="800 number"
        value={universityId}
        onChange={(event) => setUniversityId(event.target.value)}
        error={Boolean(problems.universityId)}
        helperText={problems.universityId}
      />
      <Button type="submit" variant="contained" disabled={busy} sx={{ alignSelf: "flex-start" }}>
        {busy ? "Adding..." : role === "instructor" ? "Add instructor" : "Add student"}
      </Button>
    </Stack>
  );
}