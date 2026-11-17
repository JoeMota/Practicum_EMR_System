import { useEffect, useState } from "react";
import {
  Alert, Box, Button, LinearProgress, Paper, Tab, Table, TableBody, TableCell, TableHead, TableRow, Tabs, Typography,
} from "@mui/material";
import { useLocation, useNavigate, useSearchParams } from "react-router-dom";
import { listReviewQueue } from "../../api/notes";
import { useSession } from "../auth/useSession";
import { formatDateTime } from "../../utils/format";
import { useAsync } from "../../utils/useAsync";
import NoteStatusChip from "../../components/NoteStatusChip";
import EmptyState from "../../components/EmptyState";
import PageError from "../../components/PageError";
import { usePageHeading } from "../../components/usePageHeading";
import { templateName } from "./noteTemplates";
import type { NoteStatus } from "../../types";

const FILTERS: { id: NoteStatus | "all"; label: string }[] = [
  { id: "pending_review", label: "Needs review" },
  { id: "returned", label: "Returned" },
  { id: "cosigned", label: "Co-signed" },
  { id: "all", label: "All" },
];

const QUEUE_STATUSES = new Set<NoteStatus>(["pending_review", "returned", "cosigned"]);

function tabFromSearch(value: string | null): NoteStatus | "all" {
  if (value === "all" || value === "returned" || value === "cosigned" || value === "pending_review") return value;
  return "pending_review";
}

export default function ReviewQueuePage() {
  usePageHeading("Review queue");
  const navigate = useNavigate();
  const location = useLocation();
  const [params, setParams] = useSearchParams();
  const { activeRole, courseId } = useSession();
  const incoming = (location.state as { flash?: string } | null)?.flash ?? "";
  const [flash, setFlash] = useState("");
  const [seenFlash, setSeenFlash] = useState("");
  if (incoming && incoming !== seenFlash) {
    setSeenFlash(incoming);
    setFlash(incoming);
  }
  const filter = tabFromSearch(params.get("status"));
  const queue = useAsync(() => listReviewQueue(courseId, activeRole), [courseId, activeRole]);

  useEffect(() => {
    if (!incoming) return;
    navigate(".", { replace: true, state: null });
  }, [incoming, navigate]);

  const rows = (queue.data ?? []).filter((q) => QUEUE_STATUSES.has(q.note.status));
  const items = rows.filter((q) => filter === "all" || q.note.status === filter);
  const count = (s: NoteStatus | "all") =>
    s === "all" ? rows.length : rows.filter((q) => q.note.status === s).length;

  if (queue.error) return <PageError error={queue.error} />;

  return (
    <Box>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
        Assessment notes routed to you. Scores you save stay on the note. Students do not see them.
      </Typography>

      {flash && (
        <Alert severity="success" onClose={() => setFlash("")} sx={{ mb: 2 }}>{flash}</Alert>
      )}

      <Paper>
        <Tabs
          value={filter}
          onChange={(_, v) => setParams({ status: v }, { replace: true })}
          sx={{ px: 1, borderBottom: 1, borderColor: "divider" }}
          aria-label="Filter by status"
        >
          {FILTERS.map((f) => (
            <Tab key={f.id} value={f.id} label={f.id === "all" ? `${f.label} (${count("all")})` : `${f.label} (${count(f.id)})`} />
          ))}
        </Tabs>
        {queue.loading && <LinearProgress aria-label="Loading review queue" />}
        <Box sx={{ overflowX: "auto", p: 1 }}>
          {queue.loading ? null : items.length === 0 ? (
            <Box sx={{ p: 2 }}>
              <EmptyState title={filter === "pending_review" ? "You're caught up" : "Nothing here"}>
                {filter === "pending_review"
                  ? "New submissions appear here as students sign their notes."
                  : "Try another tab to see returned or co-signed notes."}
              </EmptyState>
            </Box>
          ) : (
            <Table>
              <TableHead>
                <TableRow>
                  <TableCell>Student</TableCell>
                  <TableCell>Patient</TableCell>
                  <TableCell>Note</TableCell>
                  <TableCell>Submitted</TableCell>
                  <TableCell>Status</TableCell>
                  <TableCell align="right"><Box component="span" sx={visuallyHidden}>Actions</Box></TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {items.map(({ note, patient }) => {
                  const open = () => navigate(`/review/${note.id}`);
                  return (
                    <TableRow
                      key={note.id}
                      hover
                      onClick={open}
                      onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); open(); } }}
                      tabIndex={0}
                      sx={{ cursor: "pointer" }}
                      aria-label={`Review note by ${note.authorName}`}
                    >
                      <TableCell sx={{ fontWeight: 600 }}>{note.authorName}</TableCell>
                      <TableCell>
                        {patient.lastName}, {patient.firstName}
                        <Typography variant="caption" color="text.secondary" sx={{ display: "block" }}>MRN {patient.mrn}</Typography>
                      </TableCell>
                      <TableCell>{templateName(note.templateId)}</TableCell>
                      <TableCell>{note.signedAt ? formatDateTime(note.signedAt) : "—"}</TableCell>
                      <TableCell><NoteStatusChip status={note.status} /></TableCell>
                      <TableCell align="right" onClick={(e) => e.stopPropagation()}>
                        <Button size="small" variant={note.status === "pending_review" ? "contained" : "outlined"} onClick={open}>
                          {note.status === "pending_review" ? "Review" : "Open"}
                        </Button>
                      </TableCell>
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
          )}
        </Box>
      </Paper>
    </Box>
  );
}

const visuallyHidden = {
  position: "absolute", width: 1, height: 1, overflow: "hidden", clip: "rect(0 0 0 0)", whiteSpace: "nowrap",
} as const;
