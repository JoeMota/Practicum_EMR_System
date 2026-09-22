import { useState } from "react";
import { Alert, Box, Button, Chip, Paper, Stack, Typography } from "@mui/material";
import type { Patient } from "../../types";
import { createReferral, listAppointments, listReferrals } from "../../api/scheduling";
import { useSession } from "../auth/AuthContext";
import { can } from "../../utils/permissions";
import { disciplineLabel } from "../../utils/labels";
import { formatDate, formatDateTime } from "../../utils/format";
import { useAsync } from "../../utils/useAsync";
import ReferralDialog from "./ReferralDialog";

export default function SchedulingTab({ patient }: { patient: Patient }) {
  const { user, activeRole } = useSession();
  const [open, setOpen] = useState(false);
  const appts = useAsync(() => listAppointments(patient.id), [patient.id]);
  const refs = useAsync(() => listReferrals(patient.id), [patient.id]);

  return (
    <Box sx={{ display: "grid", gap: 2.5, gridTemplateColumns: { md: "1fr 1fr" } }}>
      {(appts.error || refs.error) && (
        <Alert severity="error" sx={{ gridColumn: "1 / -1" }}>
          {(appts.error ?? refs.error)!.message}
        </Alert>
      )}
      <Paper sx={{ p: 2.5 }}>
        <Typography component="h2" variant="h6" sx={{ mb: 1.5 }}>Upcoming appointments</Typography>
        {(appts.data ?? []).length === 0 && <Typography variant="body2" color="text.secondary">None scheduled.</Typography>}
        <Stack spacing={1.5}>
          {appts.data?.map((a) => (
            <Box key={a.id}>
              <Typography variant="body2" sx={{ fontWeight: 700 }}>{formatDateTime(a.when)}</Typography>
              <Typography variant="body2">{a.kind}, {a.withWhom}</Typography>
            </Box>
          ))}
        </Stack>
      </Paper>

      <Paper sx={{ p: 2.5 }}>
        <Box sx={{ display: "flex", alignItems: "center", mb: 1.5 }}>
          <Typography component="h2" variant="h6" sx={{ flex: 1 }}>Referrals</Typography>
          {can(activeRole, "referral:create") && <Button variant="outlined" onClick={() => setOpen(true)}>Create referral</Button>}
        </Box>
        {(refs.data ?? []).length === 0 && <Typography variant="body2" color="text.secondary">No referrals yet.</Typography>}
        <Stack spacing={1.5}>
          {refs.data?.map((r) => (
            <Box key={r.id}>
              <Box sx={{ display: "flex", gap: 1, alignItems: "center" }}>
                <Typography variant="body2" sx={{ fontWeight: 700 }}>To {disciplineLabel[r.toDiscipline]}</Typography>
                {r.urgency === "urgent" && <Chip size="small" color="error" label="Urgent" />}
              </Box>
              <Typography variant="body2">{r.reason}</Typography>
              <Typography variant="caption" color="text.secondary">{r.createdByName}, {formatDate(r.createdAt)}</Typography>
            </Box>
          ))}
        </Stack>
      </Paper>

      <ReferralDialog
        open={open}
        onClose={() => setOpen(false)}
        onCreate={async (input) => {
          await createReferral(user, { ...input, patientId: patient.id });
          refs.reload();
        }}
      />
    </Box>
  );
}
