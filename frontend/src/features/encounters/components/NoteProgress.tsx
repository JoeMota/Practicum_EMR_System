import { Step, StepLabel, Stepper, Typography } from "@mui/material";
import type { ClinicalNote } from "../../../types";
import { formatDateTime } from "../../../utils/format";

export default function NoteProgress({ note }: { note: ClinicalNote }) {
  if (note.mode === "simulation") {
    return (
      <Stepper orientation="vertical" activeStep={note.status === "signed" ? 2 : 0}>
        <Step><StepLabel>Draft</StepLabel></Step>
        <Step><StepLabel optional={note.signedAt && <Typography variant="caption">{formatDateTime(note.signedAt)}</Typography>}>Signed and closed</StepLabel></Step>
      </Stepper>
    );
  }
  if (note.mode === "practice") {
    return (
      <Stepper orientation="vertical" activeStep={note.status === "signed" ? 2 : 0}>
        <Step><StepLabel>Draft</StepLabel></Step>
        <Step><StepLabel optional={note.signedAt && <Typography variant="caption">{formatDateTime(note.signedAt)}</Typography>}>Signed (practice, not graded)</StepLabel></Step>
      </Stepper>
    );
  }
  const active = { draft: 0, returned: 1, pending_review: 1, cosigned: 3, signed: 3 }[note.status];
  return (
    <Stepper orientation="vertical" activeStep={active}>
      <Step completed={note.status !== "draft"}>
        <StepLabel>Draft</StepLabel>
      </Step>
      <Step completed={note.status === "cosigned"}>
        <StepLabel
          error={note.status === "returned"}
          optional={
            <Typography variant="caption" color={note.status === "returned" ? "error" : "text.secondary"}>
              {note.status === "returned" ? "Returned. Revise and resubmit." : note.signedAt ? `Signed ${formatDateTime(note.signedAt)}` : "Sign to submit"}
            </Typography>
          }
        >
          Needs review
        </StepLabel>
      </Step>
      <Step completed={note.status === "cosigned"}>
        <StepLabel optional={note.cosignedAt && <Typography variant="caption">{note.cosignedByName}, {formatDateTime(note.cosignedAt)}</Typography>}>
          Co-signed
        </StepLabel>
      </Step>
    </Stepper>
  );
}
