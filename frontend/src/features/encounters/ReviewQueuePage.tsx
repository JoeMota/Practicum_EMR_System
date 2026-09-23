import { useState } from "react";
import {
  Alert, Box, Button, LinearProgress, Paper, Tab, Table, TableBody, TableCell, TableHead, TableRow, Tabs, Typography,
} from "@mui/material";
import { useNavigate } from "react-router-dom";
import { listReviewQueue } from "../../api/notes";
import { getCourse } from "../../api/courses";
import { useSession } from "../auth/AuthContext";
import { formatDateTime } from "../../utils/format";
import { useAsync } from "../../utils/useAsync";
import NoteStatusChip from "../../components/NoteStatusChip";
import EmptyState from "../../components/EmptyState";
import { TEMPLATES } from "./noteTemplates";
import type { NoteStatus } from "../../types";

const FILTERS: { id: NoteStatus | "all"; label: string }[] = [
  { id: "pending_review", label: "Needs review" },
  { id: "returned", label: "Returned" },
  { id: "cosigned", label: "Co-signed" },
  { id: "all", label: "All" },
];

export default function ReviewQueuePage() {
  const navigate = useNavigate();
  const { user, courseId } = useSession();
  const [filter, setFilter] = useState<NoteStatus | "all">("pending_review");
  const queue = useAsync(() => listReviewQueue(user, courseId), [user.id, courseId]);
  const course = useAsync(() => getCourse(courseId), [courseId]);

  const items = (queue.data ?? []).filter((q) => filter === "all" || q.note.status === filter);
  const count = (s: NoteStatus) => queue.data?.filter((q) => q.note.status === s).length ?? 0;

  return (
    <Box>
      <Typography component="h1" variant="h5">Review queue</Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
        {course.data ? `${course.data.code}: ` : ""}assessment notes students routed to you
      </Typography>

      {queue.error && (
        <Alert severity="error" sx={{ mb: 2 }}>{queue.error.message}</Alert>
      )}

      <Paper>
        <Tabs value={filter} onChange={(_, v) => setFilter(v)} sx={{ px: 1, borderBottom: 1, borderColor: "divider" }} aria-label="Filter by status">
          {FILTERS.map((f) => (
            <Tab key={f.id} value={f.id} label={f.id === "all" ? f.label : `${f.label} (${count(f.id)})`} />
          ))}
        </Tabs>
        {queue.loading && <LinearProgress />}
        <Box sx={{ overflowX: "auto", p: 1 }}>
          {!queue.loading && items.length === 0 ? (
            <Box sx={{ p: 2 }}>
              <EmptyState title={filter === "pending_review" ? "You're caught up" : "Nothing here"}>
                {filter === "pending_review" ? "New submissions appear here as students sign their notes." : undefined}
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
                  <TableCell />
                </TableRow>
              </TableHead>
              <TableBody>
                {items.map(({ note, patient }) => (
                  <TableRow key={note.id} hover>
                    <TableCell sx={{ fontWeight: 600 }}>{note.authorName}</TableCell>
                    <TableCell>
                      {patient.lastName}, {patient.firstName}
                      <Typography variant="caption" color="text.secondary" sx={{ display: "block" }}>MRN {patient.mrn}</Typography>
                    </TableCell>
                    <TableCell>{TEMPLATES[note.templateId].name}</TableCell>
                    <TableCell>{note.signedAt ? formatDateTime(note.signedAt) : "—"}</TableCell>
                    <TableCell><NoteStatusChip status={note.status} /></TableCell>
                    <TableCell align="right">
                      <Button size="small" variant={note.status === "pending_review" ? "contained" : "outlined"} onClick={() => navigate(`/review/${note.id}`)}>
                        {note.status === "pending_review" ? "Review" : "Open"}
                      </Button>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </Box>
      </Paper>
    </Box>
  );
}
