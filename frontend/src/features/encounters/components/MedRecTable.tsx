import { Box, MenuItem, Table, TableBody, TableCell, TableHead, TableRow, TextField, Typography } from "@mui/material";
import type { Medication } from "../../../types";
import { type MedRecAction, type MedRecValue } from "./medRec";

const ACTIONS: MedRecAction[] = ["Continue", "Modify", "Discontinue", "Hold"];

interface Props {
  medications: Medication[];
  value: MedRecValue;
  readOnly?: boolean;
  onChange: (v: MedRecValue) => void;
}

export default function MedRecTable({ medications, value, readOnly, onChange }: Props) {
  if (medications.length === 0) {
    return <Typography variant="body2" color="text.secondary">No medications on the chart to reconcile.</Typography>;
  }
  const set = (id: string, patch: MedRecValue[string]) => onChange({ ...value, [id]: { ...value[id], ...patch } });

  return (
    <Box sx={{ overflowX: "auto" }}>
      <Table size="small">
        <TableHead>
          <TableRow>
            <TableCell>Medication on chart</TableCell>
            <TableCell sx={{ width: 170 }}>Decision</TableCell>
            <TableCell>Comment</TableCell>
          </TableRow>
        </TableHead>
        <TableBody>
          {medications.map((m) => {
            const row = value[m.id] ?? {};
            const label = `${m.name} ${m.dose}`;
            return (
              <TableRow key={m.id}>
                <TableCell>
                  <Typography variant="body2" sx={{ fontWeight: 600 }}>{label}</Typography>
                  <Typography variant="caption" color="text.secondary">{m.route}, {m.frequency.toLowerCase()}</Typography>
                </TableCell>
                <TableCell>
                  {readOnly ? (
                    <Typography variant="body2">{row.action ?? "Not reconciled"}</Typography>
                  ) : (
                    <TextField
                      select size="small" fullWidth value={row.action ?? ""}
                      onChange={(e) => set(m.id, { action: e.target.value as MedRecAction })}
                      slotProps={{ htmlInput: { "aria-label": `Decision for ${label}` } }}
                    >
                      {ACTIONS.map((a) => <MenuItem key={a} value={a}>{a}</MenuItem>)}
                    </TextField>
                  )}
                </TableCell>
                <TableCell>
                  {readOnly ? (
                    <Typography variant="body2">{row.comment || "—"}</Typography>
                  ) : (
                    <TextField
                      size="small" fullWidth value={row.comment ?? ""} placeholder="e.g. increase to 1000 mg BID"
                      onChange={(e) => set(m.id, { comment: e.target.value })}
                      slotProps={{ htmlInput: { "aria-label": `Comment for ${label}` } }}
                    />
                  )}
                </TableCell>
              </TableRow>
            );
          })}
        </TableBody>
      </Table>
    </Box>
  );
}
