import { useMemo, useState } from "react";
import { Alert, Button, Checkbox, Dialog, DialogActions, DialogContent, DialogTitle, ListItemText, ListSubheader, MenuItem, Stack, TextField, Typography } from "@mui/material";
import type { Patient, User } from "../../../types";
import { assignCase, type PatientRow } from "../../../api/patients";
import { listCases } from "../../../api/cases";
import { listRoster } from "../../../api/roster";
import { useSession } from "../../auth/useSession";
import { useAsync } from "../../../utils/useAsync";

interface Source {
  id: string;
  label: string;
  name: string;
  group: "Cases" | "Practice patients";
}

interface Props {
  open: boolean;
  rows: PatientRow[];
  initialSourceId?: string;
  onClose: () => void;
  onAssigned: (patients: Patient[]) => void;
}

export default function AssignCaseDialog({ open, rows, initialSourceId = "", onClose, onAssigned }: Props) {
  const { activeRole, courseId } = useSession();
  const roster = useAsync(() => listRoster(courseId), [courseId]);
  const cases = useAsync(() => listCases(activeRole, courseId), [courseId, activeRole]);
  const sources = useMemo(() => buildSources(cases.data ?? [], rows), [cases.data, rows]);
  const [sourceId, setSourceId] = useState(initialSourceId);
  const [ownerIds, setOwnerIds] = useState<string[]>([]);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const students = (roster.data ?? []).filter((student) => student.rosterStatus !== "inactive");
  const selected = students.filter((s) => ownerIds.includes(s.id));
  const source = sources.find((item) => item.id === sourceId);

  const submit = async () => {
    if (!sourceId || ownerIds.length === 0) {
      setError("Choose at least one student and a case.");
      return;
    }
    setBusy(true);
    setError("");
    const created: Patient[] = [];
    const problems: string[] = [];
    for (const ownerId of ownerIds) {
      try {
        created.push(await assignCase(activeRole, courseId, sourceId, ownerId));
      } catch (e) {
        const name = students.find((s) => s.id === ownerId)?.fullName ?? "A student";
        problems.push(`${name}: ${(e as Error).message}`);
      }
    }
    setBusy(false);
    if (created.length) onAssigned(created);
    if (problems.length) {
      setError(problems.join(" "));
      return;
    }
    onClose();
  };

  return (
    <Dialog open={open} onClose={onClose} fullWidth maxWidth="sm">
      <DialogTitle>Assign a case</DialogTitle>
      <DialogContent>
        <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
          Each selected student gets a private assessment copy. They will not see anyone else's notes on it.
        </Typography>
        <Stack spacing={2}>
          {error && <Alert severity="error">{error}</Alert>}
          <TextField
            select label="Students" value={ownerIds}
            onChange={(e) => setOwnerIds(typeof e.target.value === "string" ? e.target.value.split(",") : e.target.value)}
            disabled={roster.loading}
            slotProps={{ select: { multiple: true, renderValue: (v) => (v as string[]).map((id) => students.find((s) => s.id === id)?.fullName ?? id).join(", ") } }}
          >
            {students.map((s: User) => (
              <MenuItem key={s.id} value={s.id}>
                <Checkbox checked={ownerIds.includes(s.id)} />
                <ListItemText primary={s.fullName} />
              </MenuItem>
            ))}
          </TextField>
          <TextField
            select label="Case" value={sourceId} onChange={(e) => setSourceId(e.target.value)}
            disabled={Boolean(initialSourceId) || cases.loading}
          >
            {sources.map((item, index) => {
              const header = index === 0 || sources[index - 1].group !== item.group
                ? <ListSubheader key={item.group}>{item.group}</ListSubheader>
                : null;
              return [
                header,
                <MenuItem key={item.id} value={item.id}>{item.label}</MenuItem>,
              ];
            })}
          </TextField>
          {selected.length > 0 && source && (
            <Typography variant="body2" color="text.secondary">
              {selected.map((s) => s.fullName).join(" and ")} will each get {source.name} with a new MRN.
            </Typography>
          )}
        </Stack>
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose}>Cancel</Button>
        <Button variant="contained" onClick={submit} disabled={busy || !sourceId || ownerIds.length === 0}>
          Assign case
        </Button>
      </DialogActions>
    </Dialog>
  );
}

function buildSources(cases: { id: string; firstName: string; lastName: string; status: { program?: string } }[], rows: PatientRow[]): Source[] {
  const authored: Source[] = cases.map((item) => ({
    id: item.id,
    name: `${item.lastName}, ${item.firstName}`,
    label: `${item.lastName}, ${item.firstName}${item.status.program ? ` (${item.status.program})` : ""}`,
    group: "Cases",
  }));
  const practice = new Map<string, PatientRow>();
  for (const row of rows) {
    if (row.patient.mode !== "practice") continue;
    if (!practice.has(row.patient.caseTemplateId)) practice.set(row.patient.caseTemplateId, row);
  }
  const shared: Source[] = [...practice.values()].map((row) => ({
    id: row.patient.id,
    name: `${row.patient.lastName}, ${row.patient.firstName}`,
    label: `${row.patient.lastName}, ${row.patient.firstName} (practice)`,
    group: "Practice patients",
  }));
  return [...authored, ...shared];
}
