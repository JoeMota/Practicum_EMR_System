import { Box, Button, Table, TableBody, TableCell, TableHead, TableRow, Typography } from "@mui/material";
import { useNavigate } from "react-router-dom";
import type { ClinicalNote } from "../../../types";
import NoteStatusChip from "../../../components/NoteStatusChip";
import EmptyState from "../../../components/EmptyState";
import { formatDateTime } from "../../../utils/format";
import { disciplineLabel } from "../../../utils/labels";
import { TEMPLATES } from "../noteTemplates";

interface Props {
  notes: ClinicalNote[];
  patientId: string;
  reviewer?: boolean;
  emptyAction?: React.ReactNode;
}

export default function NotesList({ notes, patientId, reviewer, emptyAction }: Props) {
  const navigate = useNavigate();
  if (notes.length === 0) {
    return (
      <EmptyState title="No notes on this encounter yet" action={emptyAction}>
        {reviewer ? "Notes appear here once the student starts documenting." : "Start a note to document this visit."}
      </EmptyState>
    );
  }
  return (
    <Box sx={{ overflowX: "auto" }}>
      <Table size="small">
        <TableHead>
          <TableRow>
            <TableCell>Note</TableCell>
            <TableCell>Author</TableCell>
            <TableCell>Last updated</TableCell>
            <TableCell>Status</TableCell>
            <TableCell align="right"><Box component="span" sx={visuallyHidden}>Actions</Box></TableCell>
          </TableRow>
        </TableHead>
        <TableBody>
          {notes.map((n) => {
            const href = reviewer ? `/review/${n.id}` : `/patients/${patientId}/notes/${n.id}`;
            const open = () => navigate(href);
            const label = reviewer && n.status === "pending_review" ? "Review" : "Open";
            return (
              <TableRow
                key={n.id}
                hover
                onClick={open}
                onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); open(); } }}
                tabIndex={0}
                sx={{ cursor: "pointer" }}
                aria-label={`${label} ${TEMPLATES[n.templateId].name}`}
              >
                <TableCell>
                  <Typography variant="body2" sx={{ fontWeight: 600 }}>{TEMPLATES[n.templateId].name}</Typography>
                  <Typography variant="caption" color="text.secondary">{n.diagnoses.map((d) => d.code).join(", ") || "No diagnosis yet"}</Typography>
                </TableCell>
                <TableCell>
                  {n.authorName}
                  <Typography variant="caption" color="text.secondary" sx={{ display: "block" }}>{disciplineLabel[n.authorDiscipline]}</Typography>
                </TableCell>
                <TableCell>{formatDateTime(n.updatedAt)}</TableCell>
                <TableCell><NoteStatusChip status={n.status} /></TableCell>
                <TableCell align="right" onClick={(e) => e.stopPropagation()}>
                  <Button size="small" variant={reviewer && n.status === "pending_review" ? "contained" : "text"} onClick={open}>
                    {label}
                  </Button>
                </TableCell>
              </TableRow>
            );
          })}
        </TableBody>
      </Table>
    </Box>
  );
}

const visuallyHidden = {
  position: "absolute", width: 1, height: 1, overflow: "hidden", clip: "rect(0 0 0 0)", whiteSpace: "nowrap",
} as const;
