import { useState, type FormEvent } from "react";
import { Alert, Box, Button, LinearProgress, Stack, TextField, Typography } from "@mui/material";
import type { Discipline, User } from "../../types";
import { searchUsers } from "../../api/users";
import { enrollInCourse } from "../../api/roster";
import { roleLabel } from "../../utils/labels";
import { useAsync } from "../../utils/useAsync";

interface EnrollAccountProps {
  courseId: string;
  role: "student" | "instructor" | "course_coordinator";
  discipline: Discipline;
  onEnrolled: () => void;
}

export default function EnrollAccount({ courseId, role, discipline, onEnrolled }: EnrollAccountProps) {
  const [query, setQuery] = useState("");
  const [submitted, setSubmitted] = useState("");
  const [error, setError] = useState("");
  const [busyId, setBusyId] = useState<string>();
  const matches = useAsync(
    () => (submitted.trim().length < 2 ? Promise.resolve([] as User[]) : searchUsers(submitted.trim())),
    [submitted],
  );

  const search = (event: FormEvent) => {
    event.preventDefault();
    setError("");
    setSubmitted(query.trim());
  };

  const enroll = async (person: User) => {
    setBusyId(person.id);
    setError("");
    try {
      await enrollInCourse(courseId, person.id, role, discipline);
      onEnrolled();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusyId(undefined);
    }
  };

  return (
    <Box sx={{ flex: 1, minWidth: 0 }}>
      <Typography component="h3" variant="subtitle1" sx={{ fontWeight: 600 }}>Enroll an existing account</Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
        Search by name or email, then place that person in this class. The role and discipline above are what they receive here.
      </Typography>
      <Stack component="form" direction={{ xs: "column", sm: "row" }} spacing={1} onSubmit={search} sx={{ mt: 1.5 }}>
        <TextField
          size="small" label="Name or email" value={query} onChange={(event) => setQuery(event.target.value)}
          sx={{ flex: 1 }}
        />
        <Button type="submit" variant="outlined">Search</Button>
      </Stack>
      {error && <Alert severity="error" sx={{ mt: 1.5 }} onClose={() => setError("")}>{error}</Alert>}
      {matches.loading && submitted && <LinearProgress sx={{ mt: 1.5 }} />}
      {matches.error && <Alert severity="error" sx={{ mt: 1.5 }}>{matches.error.message}</Alert>}
      {submitted && !matches.loading && !matches.error && (matches.data ?? []).length === 0 && (
        <Typography variant="body2" color="text.secondary" sx={{ mt: 1.5 }}>No accounts match that search.</Typography>
      )}
      <Stack spacing={1} sx={{ mt: 1.5 }}>
        {(matches.data ?? []).map((person) => (
          <Stack key={person.id} direction="row" spacing={1} sx={{ alignItems: "center", justifyContent: "space-between" }}>
            <Box sx={{ minWidth: 0 }}>
              <Typography variant="body2" sx={{ fontWeight: 600 }}>{person.fullName}</Typography>
              <Typography variant="caption" color="text.secondary">{person.email}</Typography>
            </Box>
            <Button size="small" variant="contained" disabled={busyId === person.id} onClick={() => enroll(person)}>
              Enroll as {roleLabel[role].toLowerCase()}
            </Button>
          </Stack>
        ))}
      </Stack>
    </Box>
  );
}
