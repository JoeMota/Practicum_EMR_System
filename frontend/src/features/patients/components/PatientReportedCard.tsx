import type { ReactNode } from "react";
import { Alert, Box, LinearProgress, Paper, Stack, Typography } from "@mui/material";
import { getStaffIntake } from "../../../api/intake";
import { useSession } from "../../auth/useSession";
import { formatDateTime } from "../../../utils/format";
import { useAsync } from "../../../utils/useAsync";
import { utep } from "../../../theme/tokens";

function shown(value: string | boolean | string[] | undefined | null): string | null {
  if (typeof value === "boolean" || value == null) return null;
  if (Array.isArray(value)) {
    const items = value.map((item) => item.trim()).filter(Boolean);
    return items.length ? items.join(", ") : null;
  }
  const text = value.trim();
  return text || null;
}

function Row({ label, value }: { label: string; value: string }) {
  return <Typography variant="body2"><b>{label}:</b> {value}</Typography>;
}

export default function PatientReportedCard({ patientId }: { patientId: string }) {
  const { activeRole } = useSession();
  const intake = useAsync(() => getStaffIntake(patientId, activeRole), [patientId, activeRole]);

  if (intake.loading && !intake.data) return <LinearProgress aria-label="Loading patient-reported information" />;
  if (intake.error && !intake.data) return <Alert severity="error">{intake.error.message}</Alert>;
  if (!intake.data) return null;

  const card = { p: 2.5, borderRadius: "16px" } as const;
  const titleSx = { color: utep.navy, fontSize: 18, mb: 1.5 } as const;
  const data = intake.data.data;
  const lines = (pairs: [string, string | null | undefined][]) => pairs.flatMap(([label, value]) => (
    value ? [<Row key={label} label={label} value={value} />] : []
  ));
  const sections: { title: string; rows: ReactNode[] }[] = [
    { title: "Demographics", rows: lines([
      ["Preferred name", shown(data?.preferredName)],
      ["Pronouns", shown(data?.pronouns)],
      ["Gender identity", shown(data?.genderIdentity)],
      ["Race", shown(data?.race)],
      ["Ethnicity", shown(data?.ethnicity)],
      ["Marital status", shown(data?.maritalStatus)],
      ["Preferred language", shown(data?.preferredLanguage)],
      ["Interpreter needed", data?.interpreterNeeded ? "Yes" : null],
    ]) },
    { title: "Contact", rows: lines([
      ["Phone", [shown(data?.phone), shown(data?.phoneType)].filter(Boolean).join(" · ") || null],
      ["Email", shown(data?.email)],
      ["Address", [shown(data?.address), shown(data?.city), shown(data?.state), shown(data?.zipCode)].filter(Boolean).join(", ") || null],
    ]) },
    { title: "Insurance", rows: lines([
      ["Primary carrier", shown(data?.insurancePayer)],
      ["Plan type", shown(data?.insurancePlanType)],
      ["Member ID", shown(data?.insuranceMemberId)],
      ["Group number", shown(data?.insuranceGroupNumber)],
      ["Subscriber", data?.insuranceSubscriberIsPatient === false ? "Someone else" : null],
      ["Subscriber name", shown(data?.insuranceSubscriberName)],
      ["Subscriber date of birth", shown(data?.insuranceSubscriberDob)],
      ["Relationship", shown(data?.insuranceRelationship)],
      ["Effective date", shown(data?.insuranceEffectiveDate)],
      ["Secondary carrier", shown(data?.secondaryInsurancePayer)],
      ["Secondary member ID", shown(data?.secondaryInsuranceMemberId)],
      ["Secondary group number", shown(data?.secondaryInsuranceGroupNumber)],
      ["Secondary relationship", shown(data?.secondaryInsuranceRelationship)],
    ]) },
    { title: "Medical history", rows: lines([
      ["Conditions", shown((data?.conditions ?? []).map((item) => `${item.name}${item.year ? ` (${item.year})` : ""}`))],
      ["Other conditions", shown(data?.pastMedicalHistory)],
      ["Surgeries", shown((data?.surgeries ?? []).map((item) => `${item.procedure}${item.year ? ` (${item.year})` : ""}`))],
      ["Allergies", data?.noKnownAllergies && !(data.allergies ?? []).length ? "No known allergies" : shown((data?.allergies ?? []).map((item) => `${item.agent}${item.reaction ? ` — ${item.reaction}` : ""}`))],
      ["Medications", shown((data?.medications ?? []).map((item) => [item.name, item.dose, item.frequency].filter(Boolean).join(" ")))],
      ["Other surgeries or procedures", shown(data?.surgicalHistory)],
    ]) },
    { title: "Family history", rows: lines([
      ["Family", shown((data?.familyMembers ?? []).map((item) => [item.relative, item.status, item.conditions].filter(Boolean).join(" · ")))],
      ["Other family history", shown(data?.familyHistory)],
    ]) },
    { title: "Social history", rows: lines([
      ["Tobacco", [shown(data?.tobaccoUse), shown(data?.tobaccoDetail)].filter(Boolean).join(" · ") || null],
      ["Alcohol", [shown(data?.alcoholUse), shown(data?.alcoholDetail)].filter(Boolean).join(" · ") || null],
      ["Drug use", shown(data?.drugUse)],
      ["Occupation", shown(data?.occupation)],
      ["Lives with", shown(data?.livesWith)],
      ["Exercise", shown(data?.exercise)],
      ["Other notes on lifestyle", shown(data?.socialHistory)],
    ]) },
    { title: "Emergency contact and pharmacy", rows: lines([
      ["Name", shown(data?.emergencyContactName)],
      ["Phone", shown(data?.emergencyContactPhone)],
      ["Relationship", shown(data?.emergencyContactRelationship)],
      ["Preferred pharmacy", shown(data?.preferredPharmacy)],
    ]) },
  ].filter((section) => section.rows.length > 0);

  return (
    <Paper sx={card}>
      <Typography component="h2" variant="h6" sx={titleSx}>Patient-reported information</Typography>
      {intake.data.updatedAt && (
        <Typography variant="body2" color="text.secondary" sx={{ mb: 1.5 }}>
          Updated {formatDateTime(intake.data.updatedAt)}
        </Typography>
      )}
      {!intake.data.submitted ? (
        <Typography variant="body2" color="text.secondary">The patient has not submitted information yet.</Typography>
      ) : sections.length === 0 ? (
        <Typography variant="body2" color="text.secondary">Submitted, with no details filled in yet.</Typography>
      ) : (
        <Stack spacing={2}>
          {sections.map((section) => (
            <Box key={section.title}>
              <Typography variant="subtitle2" sx={{ mb: 0.5 }}>{section.title}</Typography>
              <Stack spacing={0.35}>{section.rows}</Stack>
            </Box>
          ))}
        </Stack>
      )}
    </Paper>
  );
}
