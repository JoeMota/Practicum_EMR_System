import { Alert, Box, LinearProgress, Stack, Typography } from "@mui/material";
import { getChartAnswerKey } from "../../../api/cases";
import { useAsync } from "../../../utils/useAsync";
import type { Role } from "../../../types";

export default function AnswerKeyPanel({ role, patientId }: { role: Role; patientId: string }) {
  const loaded = useAsync(() => getChartAnswerKey(role, patientId), [role, patientId]);

  return (
    <Box>
      <Typography component="h2" variant="subtitle1" sx={{ fontWeight: 700, mb: 1 }}>Answer key</Typography>
      {loaded.error && <Alert severity="error">{loaded.error.message}</Alert>}
      {!loaded.data && !loaded.error && <LinearProgress aria-label="Loading answer key" />}
      {loaded.data && <KeyBody keyData={loaded.data} />}
    </Box>
  );
}

function KeyBody({ keyData }: { keyData: Awaited<ReturnType<typeof getChartAnswerKey>> }) {
  const empty = keyData.diagnoses.length === 0 && (keyData.expectedCptCodes ?? []).length === 0 && keyData.planPoints.length === 0 && !keyData.rationale.trim();
  if (empty) {
    return <Typography variant="body2" color="text.secondary">No answer key for this case.</Typography>;
  }
  return (
    <Stack spacing={1.5}>
      {keyData.diagnoses.map((item) => (
        <Box key={`${item.rank}-${item.code}`}>
          <Typography variant="body2"><b>{item.rank}. {item.code}</b> {item.label}</Typography>
          {item.rationale && <Typography variant="body2" color="text.secondary">{item.rationale}</Typography>}
        </Box>
      ))}
      {keyData.expectedCptCodes?.length > 0 && (
        <Box>
          <Typography variant="subtitle2">Expected CPT codes</Typography>
          {keyData.expectedCptCodes.map((item) => (
            <Typography key={item.code} variant="body2">{item.code} {item.label}</Typography>
          ))}
        </Box>
      )}
      {keyData.planPoints.length > 0 && (
        <Box>
          <Typography variant="subtitle2">Plan points</Typography>
          {keyData.planPoints.map((point) => (
            <Typography key={point} variant="body2">{point}</Typography>
          ))}
        </Box>
      )}
      {keyData.rationale.trim() && (
        <Box>
          <Typography variant="subtitle2">Rationale</Typography>
          <Typography variant="body2" sx={{ whiteSpace: "pre-wrap" }}>{keyData.rationale}</Typography>
        </Box>
      )}
    </Stack>
  );
}
