import { Alert, Box, List, ListItem, ListItemText, Typography } from "@mui/material";
import { rubricForFile } from "../rubrics";

export default function CourseRubricPanel({ fileName }: { fileName?: string | null }) {
  const rubric = rubricForFile(fileName);
  if (!fileName) return null;

  if (!rubric) {
    return (
      <Alert severity="info" icon={false} sx={{ mt: 1.5 }}>
        Course rubric on file: <b>{fileName}</b>.
      </Alert>
    );
  }

  return (
    <Box
      sx={{
        mt: 1.5,
        p: 1.5,
        borderRadius: 1,
        border: 1,
        borderColor: "divider",
        bgcolor: "rgba(14,34,80,0.03)",
      }}
    >
      <Typography variant="subtitle2" sx={{ fontWeight: 700 }}>{rubric.title}</Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5, mb: 1 }}>
        {rubric.overview}
      </Typography>
      <Typography variant="caption" color="text.secondary" sx={{ display: "block", mb: 0.5 }}>
        Reference: {rubric.fileName}
      </Typography>
      <List dense disablePadding>
        {rubric.criteria.map((c) => (
          <ListItem key={c.id} alignItems="flex-start" sx={{ px: 0, py: 0.5 }}>
            <ListItemText
              primary={<Typography variant="body2" sx={{ fontWeight: 700 }}>{c.label}</Typography>}
              secondary={<Typography variant="caption" color="text.secondary">{c.detail}</Typography>}
            />
          </ListItem>
        ))}
      </List>
    </Box>
  );
}
