import { Alert, Box, LinearProgress, Stack, Typography } from "@mui/material";
import { getChartTriggers } from "../../../api/cases";
import { useAsync } from "../../../utils/useAsync";
import type { Role } from "../../../types";

export default function TriggersPanel({ role, patientId }: { role: Role; patientId: string }) {
  const loaded = useAsync(() => getChartTriggers(role, patientId), [role, patientId]);
  const rows = loaded.data?.triggers ?? [];

  return (
    <Box sx={{ mt: 2 }}>
      <Typography component="h3" variant="subtitle2" sx={{ fontWeight: 700 }}>Planted triggers</Typography>
      <Typography variant="caption" color="text.secondary" sx={{ display: "block", mb: 1 }}>
        For grading only. Hidden from the student, and hidden here after co-sign.
      </Typography>
      {loaded.error && <Alert severity="error">{loaded.error.message}</Alert>}
      {!loaded.data && !loaded.error && <LinearProgress aria-label="Loading planted triggers" />}
      {loaded.data && rows.length === 0 && (
        <Typography variant="body2" color="text.secondary">No planted triggers on this case.</Typography>
      )}
      {rows.length > 0 && (
        <Stack spacing={1}>
          {rows.map((item, index) => (
            <Box key={`${index}-${item.finding}`}>
              <Typography variant="body2" sx={{ fontWeight: 700 }}>{index + 1}. {item.finding}</Typography>
              {item.explanation && <Typography variant="body2" color="text.secondary">{item.explanation}</Typography>}
            </Box>
          ))}
        </Stack>
      )}
    </Box>
  );
}
