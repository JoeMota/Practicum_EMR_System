import { Box, Stack, Typography } from "@mui/material";
import type { NoteComment } from "../../../types";
import { formatDateTime } from "../../../utils/format";

const KIND_LABEL: Record<NoteComment["kind"], string> = {
  returned: "Returned for revision",
  cosigned: "Co-signed",
  comment: "Comment",
};

const SECTION_LABEL: Record<NonNullable<NoteComment["sectionId"]>, string> = {
  S: "Subjective",
  O: "Objective",
  MR: "Medication reconciliation",
  A: "Assessment",
  P: "Plan",
};

export default function FeedbackThread({ items, hideSection = false }: { items: NoteComment[]; hideSection?: boolean }) {
  if (items.length === 0) return null;
  return (
    <Stack spacing={1.5}>
      {items.map((c) => {
        const section = !hideSection && c.sectionId ? `${SECTION_LABEL[c.sectionId]} — ` : "";
        const tone = c.kind === "returned" ? "error.main" : c.kind === "comment" ? "info.main" : "success.main";
        return (
          <Box key={c.id} sx={{ borderLeft: 3, borderColor: tone, pl: 1.5 }}>
            <Typography variant="caption" color="text.secondary">
              {section}{KIND_LABEL[c.kind]} by {c.authorName}, {formatDateTime(c.createdAt)}
            </Typography>
            <Typography variant="body2" sx={{ whiteSpace: "pre-wrap" }}>{c.body}</Typography>
          </Box>
        );
      })}
    </Stack>
  );
}
