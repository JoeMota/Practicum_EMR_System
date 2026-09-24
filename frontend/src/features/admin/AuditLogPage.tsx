import { useMemo, useState } from "react";
import {
  Alert, Box, Chip, FormControlLabel, LinearProgress, Paper, Stack, Switch, Table, TableBody,
  TableCell, TableHead, TableRow, TextField, Typography,
} from "@mui/material";
import type { AuditEntry } from "../../types";
import { listAudit } from "../../api/audit";
import { formatDateTime } from "../../utils/format";
import { useAsync } from "../../utils/useAsync";
import EmptyState from "../../components/EmptyState";

/** Fallback labels when mocking or older API payloads omit actionLabel. */
const ACTION_LABELS: Record<string, string> = {
  "auth.sign_in": "Signed in",
  "auth.login": "Signed in",
  "auth.login_failed": "Sign-in failed",
  "auth.sso_sign_in": "Signed in with UTEP",
  "auth.password_changed": "Changed password",
  "chart.view": "Opened patient chart",
  "patient.update_status": "Updated patient status",
  "patient.reset_practice": "Reset practice patient",
  "note.view": "Opened clinical note",
  "note.create": "Started a clinical note",
  "note.sign": "Signed note",
  "note.sign_submit": "Submitted note for review",
  "note.cosign": "Co-signed note",
  "note.return": "Returned note for revision",
  "note.addendum": "Added note addendum",
  "roster.import": "Imported roster spreadsheet",
  "roster.add_member": "Added person to course",
  "roster.remove": "Removed person from course",
  "referral.create": "Created referral",
};

function labelFor(entry: AuditEntry): string {
  return entry.actionLabel || ACTION_LABELS[entry.action] || entry.action.replace(/[._]/g, " ");
}

function recordFor(entry: AuditEntry): string {
  if (entry.recordLabel) return entry.recordLabel;
  const [kind, id] = entry.entity.split("/");
  if (!id) return kind || "—";
  return `${kind} · ${id.slice(0, 8)}`;
}

/** Who viewed or changed what, and when — readable for instructors/admins. */
export default function AuditLogPage() {
  const { data = [], loading, error } = useAsync(() => listAudit(), []);
  const [q, setQ] = useState("");
  const [deniedOnly, setDeniedOnly] = useState(false);

  const rows = useMemo(() => {
    const needle = q.trim().toLowerCase();
    return data.filter((a) => {
      if (deniedOnly && a.result !== "denied") return false;
      if (!needle) return true;
      const hay = [a.actorName, labelFor(a), recordFor(a), a.detail, a.action, a.entity]
        .filter(Boolean)
        .join(" ")
        .toLowerCase();
      return hay.includes(needle);
    });
  }, [data, q, deniedOnly]);

  return (
    <Stack spacing={2} sx={{ animation: "emrFadeIn 220ms ease-out" }}>
      <Box sx={{ display: "flex", alignItems: "flex-end", gap: 2, flexWrap: "wrap" }}>
        <Box sx={{ flex: 1, minWidth: 220 }}>
          <Typography component="h1" variant="h5">Activity log</Typography>
          <Typography variant="body2" color="text.secondary" sx={{ maxWidth: "70ch" }}>
            A read-only trail of sign-ins, chart views, note actions, and roster changes. Entries cannot be edited or deleted.
          </Typography>
        </Box>
        <TextField
          size="small"
          placeholder="Search person, action, or record"
          value={q}
          onChange={(e) => setQ(e.target.value)}
          slotProps={{ htmlInput: { "aria-label": "Filter activity" } }}
          sx={{ width: { xs: "100%", sm: 300 } }}
        />
        <FormControlLabel
          control={<Switch checked={deniedOnly} onChange={(e) => setDeniedOnly(e.target.checked)} />}
          label="Denied only"
        />
      </Box>

      {error && <Alert severity="error">{error.message}</Alert>}

      <Paper>
        {loading && <LinearProgress aria-label="Loading activity" />}
        {!loading && rows.length === 0 ? (
          <Box sx={{ p: 3 }}>
            <EmptyState title={q || deniedOnly ? "No matching activity" : "No activity recorded yet"}>
              Chart views, note actions, roster changes, and sign-ins appear here as the class uses the system.
            </EmptyState>
          </Box>
        ) : (
          <Box sx={{ overflowX: "auto" }}>
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell sx={{ minWidth: 150 }}>When</TableCell>
                  <TableCell sx={{ minWidth: 140 }}>Who</TableCell>
                  <TableCell sx={{ minWidth: 200 }}>What happened</TableCell>
                  <TableCell sx={{ minWidth: 220 }}>About</TableCell>
                  <TableCell sx={{ minWidth: 110 }}>Result</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {rows.map((a) => (
                  <TableRow key={a.id} hover sx={a.result === "denied" ? { bgcolor: "#FEF3F2" } : undefined}>
                    <TableCell sx={{ whiteSpace: "nowrap", color: "text.secondary" }}>
                      {formatDateTime(a.timestamp)}
                    </TableCell>
                    <TableCell sx={{ fontWeight: 600 }}>{a.actorName || "System"}</TableCell>
                    <TableCell>
                      <Typography variant="body2" sx={{ fontWeight: 600 }}>{labelFor(a)}</Typography>
                      {a.detail && (
                        <Typography variant="caption" color="text.secondary" sx={{ display: "block" }}>
                          {a.detail}
                        </Typography>
                      )}
                    </TableCell>
                    <TableCell>
                      <Typography variant="body2">{recordFor(a)}</Typography>
                    </TableCell>
                    <TableCell>
                      <Chip
                        size="small"
                        label={a.result === "denied" ? "Denied" : "Allowed"}
                        color={a.result === "denied" ? "error" : "success"}
                        variant={a.result === "denied" ? "filled" : "outlined"}
                      />
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </Box>
        )}
      </Paper>
    </Stack>
  );
}
