import { Alert, Box, Button, Chip, Container, LinearProgress, Paper, Stack, Table, TableBody, TableCell, TableHead, TableRow, Typography } from "@mui/material";
import { useSearchParams } from "react-router-dom";
import { request } from "../../api/client";
import { emptyIntake, getPortalIntake, type PortalIntake } from "../../api/intake";
import { useAsync } from "../../utils/useAsync";
import { formatDate } from "../../utils/format";
import { brandAccentBar, utep } from "../../theme/tokens";
import PageError from "../../components/PageError";
import { usePageHeading } from "../../components/usePageHeading";
import PatientIntakeForm from "./PatientIntakeForm";
import { intakeCompleteness } from "./intakeUtils";

interface PortalChart {
  patient: { name: string; dob: string; mrn: string };
  labs: { name: string; value: string; unit: string; reference_range: string; flag?: string; collected_at?: string }[];
  last_visit: { date?: string; type?: string; summary?: string | null };
  prescribed_medications: { name: string; dose: string; route: string; frequency: string }[];
  medication_list: { name: string; dose: string; route: string; frequency: string; prescribed: boolean }[];
  insurance?: { payer?: string | null; member_id?: string | null; group_number?: string | null };
}

const PREVIEW_CHART: PortalChart = {
  patient: { name: "Alex Morgan", dob: "1994-06-12", mrn: "MR-2048" },
  labs: [
    { name: "Lipid panel", value: "168", unit: "mg/dL", reference_range: "< 200", collected_at: "2026-10-21" },
    { name: "Hemoglobin A1c", value: "5.8", unit: "%", reference_range: "4.0–5.6", flag: "H", collected_at: "2026-08-13" },
    { name: "Potassium", value: "4.2", unit: "mmol/L", reference_range: "3.5–5.1", collected_at: "2026-05-02" },
  ],
  last_visit: {
    date: "2026-10-21",
    type: "Office visit",
    summary: "Reviewed home blood pressure readings. Continue current medication and follow up in three months.",
  },
  prescribed_medications: [
    { name: "Lisinopril", dose: "10 mg", route: "oral", frequency: "once daily" },
  ],
  medication_list: [
    { name: "Lisinopril", dose: "10 mg", route: "oral", frequency: "once daily", prescribed: true },
    { name: "Vitamin D3", dose: "1000 IU", route: "oral", frequency: "once daily", prescribed: false },
  ],
  insurance: { payer: "University plan", member_id: "M-2048", group_number: "UTEP" },
};

const PREVIEW_INTAKE: PortalIntake = {
  data: {
    ...emptyIntake(),
    preferredName: "Alex",
    pronouns: "they/them",
    genderIdentity: "Non-binary",
    race: ["White"],
    ethnicity: "Prefer not to say",
    maritalStatus: "Single",
    email: "alex.morgan@portal.test",
    phone: "915-555-0148",
    phoneType: "Mobile",
    address: "100 Maple Avenue",
    city: "El Paso",
    state: "TX",
    zipCode: "79901",
    preferredLanguage: "English",
    insurancePayer: "Valley Health Plan",
    insuranceMemberId: "VHP-2048",
    insuranceGroupNumber: "VHP-10",
    insurancePlanType: "PPO",
    insuranceSubscriberIsPatient: true,
    conditions: [{ name: "Asthma", year: "2018" }],
    allergies: [{ agent: "Penicillin", reaction: "Rash" }],
    medications: [{ name: "Lisinopril", dose: "10 mg", frequency: "once daily" }],
    familyMembers: [{ relative: "Mother", status: "Living", conditions: "Hypertension" }],
    tobaccoUse: "Never",
    alcoholUse: "Occasional",
    emergencyContactName: "Jordan Morgan",
    emergencyContactPhone: "915-555-0182",
    emergencyContactRelationship: "Sibling",
    confirmedAccurate: true,
  },
  identity: { firstName: "Alex", lastName: "Morgan", dob: "1994-06-12", sexAtBirth: "Female", mrn: "MR-2048" },
  source: "patient",
  updatedAt: "2026-10-21T15:00:00Z",
  editable: false,
  notEditableReason: null,
};

const TABS = [
  { id: "overview", label: "Overview" },
  { id: "health-record", label: "Health record" },
  { id: "my-information", label: "My information" },
] as const;
type TabId = (typeof TABS)[number]["id"];

function Overview({ chart, intake, onComplete }: { chart: PortalChart; intake: PortalIntake; onComplete: () => void }) {
  return (
    <Stack spacing={2}>
      <Box sx={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 2, flexWrap: "wrap" }}>
        <Box>
          <Typography component="h1" variant="h5" sx={{ fontWeight: 700 }}>{chart.patient.name}</Typography>
          <Typography variant="body2" color="text.secondary">
            DOB {formatDate(chart.patient.dob)} · MRN {chart.patient.mrn}
          </Typography>
        </Box>
      </Box>
      <ProfileCompleteness intake={intake} onComplete={onComplete} />
      <Paper sx={{ p: 2.5, borderRadius: "16px" }}>
        <Typography component="h2" variant="h6" sx={{ mb: 1.5 }}>Last visit</Typography>
        <Typography variant="body2" color="text.secondary">
          {chart.last_visit.type || "No visit on file"}{chart.last_visit.date ? ` · ${formatDate(chart.last_visit.date)}` : ""}
        </Typography>
        <Typography variant="body2" sx={{ whiteSpace: "pre-wrap", mt: 1 }}>
          {chart.last_visit.summary || "No signed note is on this chart yet."}
        </Typography>
      </Paper>
      <Paper sx={{ p: 2.5, borderRadius: "16px" }}>
        <Typography component="h2" variant="h6" sx={{ mb: 1.5 }}>Coverage</Typography>
        <Stack spacing={0.5}>
          <ValueRow label="Primary carrier" value={intake.data.insurancePayer} />
          <ValueRow label="Plan type" value={intake.data.insurancePlanType} />
          <ValueRow label="Member ID" value={intake.data.insuranceMemberId} />
          <ValueRow label="Group number" value={intake.data.insuranceGroupNumber} />
          <ValueRow label="Subscriber" value={intake.data.insuranceSubscriberIsPatient ? "Patient" : intake.data.insuranceSubscriberName} />
          <ValueRow label="Relationship" value={intake.data.insuranceRelationship} />
          <ValueRow label="Effective date" value={intake.data.insuranceEffectiveDate ?? ""} />
          <ValueRow label="Secondary carrier" value={intake.data.secondaryInsurancePayer} />
          <ValueRow label="Secondary member ID" value={intake.data.secondaryInsuranceMemberId} />
          <ValueRow label="Secondary group number" value={intake.data.secondaryInsuranceGroupNumber} />
          <ValueRow label="Secondary relationship" value={intake.data.secondaryInsuranceRelationship} />
        </Stack>
      </Paper>
      <Paper sx={{ p: 2.5, borderRadius: "16px" }}>
        <Typography component="h2" variant="h6" sx={{ mb: 1.5 }}>Prescribed medications</Typography>
        {chart.prescribed_medications.length === 0 ? (
          <Typography variant="body2" color="text.secondary">None on file.</Typography>
        ) : (
          <Stack spacing={0.5}>
            {chart.prescribed_medications.map((item, index) => (
              <Typography key={`${item.name}-${index}`} variant="body2">
                {item.name} {item.dose} {item.route} {item.frequency}
              </Typography>
            ))}
          </Stack>
        )}
      </Paper>
    </Stack>
  );
}

function ProfileCompleteness({ intake, onComplete }: { intake: PortalIntake; onComplete: () => void }) {
  const completeness = intakeCompleteness(intake.data);
  return (
    <Paper sx={{ p: 2.5, borderRadius: "16px" }}>
      <Box sx={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 1, mb: 1 }}>
        <Typography component="h2" variant="h6">Profile completeness</Typography>
        <Typography variant="body2" color="text.secondary">{completeness.done} of {completeness.total} sections complete</Typography>
      </Box>
      <LinearProgress variant="determinate" value={completeness.total ? (completeness.done / completeness.total) * 100 : 0} sx={{ mb: 1.5 }} />
      <Button variant="contained" onClick={onComplete}>Complete your information</Button>
    </Paper>
  );
}

function ValueRow({ label, value }: { label: string; value: string }) {
  if (!value.trim()) return null;
  return <Typography variant="body2"><b>{label}:</b> {value}</Typography>;
}

function HealthRecord({ chart, intake }: { chart: PortalChart; intake: PortalIntake }) {
  const medicationRows = chart.medication_list;
  const allergies = intake.data.allergies;
  return (
    <Stack spacing={2}>
      <Paper sx={{ p: 2.5, borderRadius: "16px" }}>
        <Typography component="h2" variant="h6" sx={{ mb: 1.5 }}>Labs</Typography>
        {chart.labs.length === 0 ? <Typography variant="body2" color="text.secondary">None on file.</Typography> : (
          <Box sx={{ overflowX: "auto" }}>
            <Table size="small">
              <TableHead><TableRow><TableCell>Test</TableCell><TableCell>Result</TableCell><TableCell>Reference range</TableCell><TableCell>Collected</TableCell></TableRow></TableHead>
              <TableBody>
                {chart.labs.map((lab, index) => (
                  <TableRow key={`${lab.name}-${index}`}>
                    <TableCell>{lab.name}</TableCell>
                    <TableCell>{lab.value} {lab.unit} {lab.flag && <Chip size="small" color="warning" label={lab.flag} />}</TableCell>
                    <TableCell>{lab.reference_range}</TableCell>
                    <TableCell>{lab.collected_at ? formatDate(lab.collected_at) : "—"}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </Box>
        )}
      </Paper>
      <Paper sx={{ p: 2.5, borderRadius: "16px" }}>
        <Typography component="h2" variant="h6" sx={{ mb: 1.5 }}>Medication list</Typography>
        {medicationRows.length === 0 ? <Typography variant="body2" color="text.secondary">None on file.</Typography> : (
          <Box sx={{ overflowX: "auto" }}>
            <Table size="small">
              <TableHead><TableRow><TableCell>Medication</TableCell><TableCell>Dose</TableCell><TableCell>Route</TableCell><TableCell>Frequency</TableCell><TableCell>Status</TableCell></TableRow></TableHead>
              <TableBody>
                {medicationRows.map((item, index) => (
                  <TableRow key={`${item.name}-${index}`}>
                    <TableCell>{item.name}</TableCell><TableCell>{item.dose}</TableCell><TableCell>{item.route}</TableCell><TableCell>{item.frequency}</TableCell>
                    <TableCell><Chip size="small" label={item.prescribed ? "Prescribed" : "Reported"} color={item.prescribed ? "primary" : "default"} /></TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </Box>
        )}
        {intake.data.medications.length > 0 && (
          <>
            <Typography variant="subtitle2" sx={{ mt: 2 }}>Patient-reported medications</Typography>
            <Stack spacing={0.5} sx={{ mt: 0.5 }}>
              {intake.data.medications.map((item, index) => <Typography key={`${item.name}-${index}`} variant="body2">{item.name} {item.dose} {item.frequency}</Typography>)}
            </Stack>
          </>
        )}
        {(intake.data.noKnownAllergies || allergies.length > 0) && (
          <>
            <Typography variant="subtitle2" sx={{ mt: 2 }}>Patient-reported allergies</Typography>
            {intake.data.noKnownAllergies && allergies.length === 0 ? (
              <Typography variant="body2">No known allergies.</Typography>
            ) : (
              <Stack spacing={0.5} sx={{ mt: 0.5 }}>
                {allergies.map((item, index) => <Typography key={`${item.agent}-${index}`} variant="body2">{item.agent}{item.reaction ? ` — ${item.reaction}` : ""}</Typography>)}
              </Stack>
            )}
          </>
        )}
      </Paper>
    </Stack>
  );
}

export default function PatientPortalPage({ previewMode = false }: { previewMode?: boolean }) {
  usePageHeading(previewMode ? "Patient portal preview" : "My chart");
  const [params, setParams] = useSearchParams();
  const tab = (TABS.find((item) => item.id === params.get("tab"))?.id ?? "overview") as TabId;
  const chart = useAsync(
    () => previewMode ? Promise.resolve(PREVIEW_CHART) : request<PortalChart>("/portal", { query: { role: "patient" } }),
    [previewMode],
  );
  const intake = useAsync(
    () => previewMode ? Promise.resolve(PREVIEW_INTAKE) : getPortalIntake(),
    [previewMode],
  );
  if (chart.error) return <PageError error={chart.error} />;
  if (intake.error) return <PageError error={intake.error} />;
  if (!chart.data || !intake.data) return <LinearProgress aria-label="Loading patient portal" />;
  const setTab = (next: TabId) => setParams({ tab: next }, { replace: true });
  const portal = (
    <Box role="tabpanel" aria-label={TABS.find((item) => item.id === tab)?.label}>
      {tab === "overview" && <Overview chart={chart.data} intake={intake.data} onComplete={() => setTab("my-information")} />}
      {tab === "health-record" && <HealthRecord chart={chart.data} intake={intake.data} />}
      {tab === "my-information" && <PatientIntakeForm intake={intake.data} onSaved={intake.setData} previewMode={previewMode} />}
    </Box>
  );

  if (!previewMode) return portal;
  return (
    <Container maxWidth="md" sx={{ py: 4 }}>
      <Box
        component="header"
        sx={{ mb: 2, overflow: "hidden", bgcolor: utep.paper, color: utep.navy, boxShadow: `inset 0 0 0 1px ${utep.lineSoft}` }}
      >
        <Box aria-hidden sx={{ height: 3, background: brandAccentBar }} />
        <Stack direction={{ xs: "column", sm: "row" }} spacing={2} sx={{ alignItems: { sm: "center" }, justifyContent: "space-between", p: { xs: 2, sm: 3 } }}>
          <Box>
            <Typography variant="overline" sx={{ fontWeight: 700, letterSpacing: "0.06em", color: utep.ink2 }}>Patient portal</Typography>
            <Typography component="h1" variant="h4" sx={{ lineHeight: 1.15 }}>Your health, at a glance</Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>Visit details, medications, and recent lab results.</Typography>
          </Box>
        </Stack>
      </Box>
      <Alert severity="info" sx={{ mb: 2 }}>Preview only. Nothing is saved.</Alert>
      {portal}
    </Container>
  );
}
