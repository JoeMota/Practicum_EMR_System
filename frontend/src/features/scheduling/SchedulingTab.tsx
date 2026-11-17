import { useState } from "react";
import { Box, Button, Chip, Paper, Stack, Typography } from "@mui/material";
import type { Patient } from "../../types";
import { createReferral, listAppointments, listReferrals } from "../../api/scheduling";
import { useSession } from "../auth/useSession";
import { can } from "../../utils/permissions";
import { disciplineLabel } from "../../utils/labels";
import { formatDate, formatDateTime } from "../../utils/format";
import { useAsync } from "../../utils/useAsync";
import ReferralDialog from "./ReferralDialog";

export default function SchedulingTab({ patient, section = "both" }: { patient: Patient; section?: "appointments" | "referrals" | "both" }) {
  const { activeRole } = useSession();
  const [open, setOpen] = useState(false);
  const appts = useAsync(() => listAppointments(patient.id, activeRole), [patient.id, activeRole]);
  const refs = useAsync(() => listReferrals(patient.id, activeRole), [patient.id, activeRole]);

  return (
    <Box sx={{ display: "grid", gap: 2.5, gridTemplateColumns: section === "both" ? { md: "1fr 1fr" } : "1fr" }}>
      {(section === "both" || section === "appointments") && <Paper sx={{ p: 2.5, borderRadius: "16px" }}>
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
      </Paper>}

      {(section === "both" || section === "referrals") && <Paper sx={{ p: 2.5, borderRadius: "16px" }}>
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
      </Paper>}

      <ReferralDialog
        open={open}
        onClose={() => setOpen(false)}
        onCreate={async (input) => {
          await createReferral(activeRole, { ...input, patientId: patient.id });
          refs.reload();
        }}
      />
    </Box>
  );
}
