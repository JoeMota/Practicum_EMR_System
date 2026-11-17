import { useState, type FormEvent } from "react";
import { Button, Stack, TextField } from "@mui/material";
import type { Discipline, RosterRow } from "../../types";
import { validateRosterRow } from "./parseRoster";

function validateStaffRow(row: { fullName: string; email: string; universityId: string }) {
  if (!row.fullName) return { ...row, problem: "Missing name" };
  if (!row.email) return { ...row, problem: "Email is required" };
  return { ...row, problem: undefined };
}

interface AddPersonFormProps {
  role: "student" | "instructor" | "course_coordinator";
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
    const validated = role === "student" ? validateRosterRow(row) : validateStaffRow(row);
    if (validated.problem) {
      const field = validated.problem === "Missing name"
        ? "fullName"
        : validated.problem === "Email is required"
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
      {role === "student" && (
        <TextField
          size="small"
          label="800 number"
          value={universityId}
          onChange={(event) => setUniversityId(event.target.value)}
          error={Boolean(problems.universityId)}
          helperText={problems.universityId}
        />
      )}
      <Button type="submit" variant="contained" disabled={busy} sx={{ alignSelf: "flex-start" }}>
        {busy ? "Adding..." : role === "instructor" ? "Add instructor" : role === "course_coordinator" ? "Add course coordinator" : "Add student"}
      </Button>
    </Stack>
  );
}