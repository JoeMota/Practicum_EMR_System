import { useState, type FormEvent } from "react";
import {
  Alert, Box, Breadcrumbs, Button, Checkbox, FormControlLabel, LinearProgress, Link, MenuItem, Paper, Stack, TextField, Typography,
} from "@mui/material";
import { Link as RouterLink, useNavigate, useParams } from "react-router-dom";
import { createCase, getCase, updateCase, type CaseInput } from "../../api/cases";
import { savePatientPhoto } from "../../api/patients";
import { useSession } from "../auth/useSession";
import { useAsync } from "../../utils/useAsync";
import { usePageHeading } from "../../components/usePageHeading";
import PageError from "../../components/PageError";
import AnswerKeyEditor from "./AnswerKeyEditor";
import CaseRubricPanel from "./CaseRubricPanel";
import CaseTriggersEditor from "./CaseTriggersEditor";
import EditableTable from "./EditableTable";
import type { AuthoredCase, CareSetting, CodeStatus, EncounterStatus, LifecycleStatus } from "../../types";

const LIFECYCLE: LifecycleStatus[] = ["Active", "Inactive", "Prospective", "Discharged from practice", "Archived", "Deceased"];
const ENCOUNTER: EncounterStatus[] = ["Scheduled", "Checked in", "Roomed", "In progress", "Checked out", "Closed"];
const SETTING: CareSetting[] = ["Outpatient", "Inpatient", "Emergency", "Discharged"];
const CODE_STATUS: Array<CodeStatus | ""> = ["", "Full code", "DNR", "DNI", "Other"];

interface Draft {
  firstName: string;
  lastName: string;
  preferredName: string;
  dob: string;
  sexAtBirth: "Male" | "Female";
  pronouns: string;
  chiefComplaint: string;
  hpi: string;
  pastMedicalHistory: string;
  surgicalHistory: string;
  familyHistory: string;
  socialHistory: string;
  insurancePayer: string;
  insuranceMemberId: string;
  insuranceGroupNumber: string;
  insuranceNotes: string;
  emergencyContactName: string;
  emergencyContactPhone: string;
  emergencyContactRelationship: string;
  codeStatus: CodeStatus | "";
  advanceDirectiveNotes: string;
  hipaaOnFile: boolean;
  hipaaNote: string;
  encounterType: string;
  careSetting: CareSetting;
  lifecycle: LifecycleStatus;
  encounterStatus: EncounterStatus;
  program: string;
  allergies: Record<string, string>[];
  medications: Record<string, string>[];
  problems: Record<string, string>[];
  labs: Record<string, string>[];
  vitals: Record<string, string>[];
  lungSounds: Record<string, string>[];
  sectionLocks: Record<string, boolean>;
  prefillSections: string[];
  unit: string;
  room: string;
  bed: string;
}

const STUDENT_SECTIONS = [
  ["medications", "Medications"],
  ["allergies", "Allergies"],
  ["vitals", "Vitals"],
  ["lung_sounds", "Lung sounds"],
  ["labs", "Labs"],
  ["diagnoses", "Diagnoses"],
  ["medical_history", "Past medical history"],
  ["surgical_history", "Surgical history"],
  ["chief_complaint", "Chief complaint"],
] as const;

const PREFILL = [
  ["chief_complaint", "Chief complaint"],
  ["hpi", "HPI"],
  ["vitals", "Vitals"],
  ["labs", "Labs"],
  ["history", "History"],
  ["medications", "Medications"],
  ["diagnoses", "Diagnoses"],
] as const;

const DEFAULT_LOCKS: Record<string, boolean> = {
  medications: false, allergies: false, vitals: false, lung_sounds: false, labs: false,
  diagnoses: true, medical_history: true, surgical_history: true, chief_complaint: true,
};

function emptyDraft(): Draft {
  return {
    firstName: "", lastName: "", preferredName: "", dob: "", sexAtBirth: "Female", pronouns: "",
    chiefComplaint: "", hpi: "", pastMedicalHistory: "", surgicalHistory: "", familyHistory: "", socialHistory: "",
    insurancePayer: "", insuranceMemberId: "", insuranceGroupNumber: "", insuranceNotes: "",
    emergencyContactName: "", emergencyContactPhone: "", emergencyContactRelationship: "",
    codeStatus: "Full code", advanceDirectiveNotes: "", hipaaOnFile: true, hipaaNote: "",
    encounterType: "Office visit", careSetting: "Outpatient", lifecycle: "Active", encounterStatus: "Scheduled",
    program: "", allergies: [], medications: [], problems: [], labs: [], vitals: [], lungSounds: [],
    sectionLocks: { ...DEFAULT_LOCKS }, prefillSections: [], unit: "", room: "", bed: "",
  };
}

function row(values: Record<string, string | undefined>): Record<string, string> {
  const out: Record<string, string> = { id: crypto.randomUUID() };
  for (const [key, value] of Object.entries(values)) out[key] = value ?? "";
  return out;
}

function draftFrom(item: AuthoredCase): Draft {
  return {
    firstName: item.firstName,
    lastName: item.lastName,
    preferredName: item.preferredName ?? "",
    dob: item.dob.slice(0, 10),
    sexAtBirth: item.sexAtBirth,
    pronouns: item.pronouns ?? "",
    chiefComplaint: item.chiefComplaint,
    hpi: item.hpi,
    pastMedicalHistory: item.pastMedicalHistory,
    surgicalHistory: item.surgicalHistory,
    familyHistory: item.familyHistory,
    socialHistory: item.socialHistory,
    insurancePayer: item.insurance?.payer ?? "",
    insuranceMemberId: item.insurance?.memberId ?? "",
    insuranceGroupNumber: item.insurance?.groupNumber ?? "",
    insuranceNotes: item.insurance?.notes ?? "",
    emergencyContactName: item.emergencyContact?.name ?? "",
    emergencyContactPhone: item.emergencyContact?.phone ?? "",
    emergencyContactRelationship: item.emergencyContact?.relationship ?? "",
    codeStatus: (item.codeStatus as CodeStatus | undefined) ?? "",
    advanceDirectiveNotes: item.advanceDirectiveNotes ?? "",
    hipaaOnFile: Boolean(item.hipaaOnFile),
    hipaaNote: item.hipaaNote ?? "",
    encounterType: item.encounter.type,
    careSetting: item.status.careSetting,
    lifecycle: item.status.lifecycle,
    encounterStatus: item.status.encounter,
    program: item.status.program ?? "",
    allergies: item.allergies.map((a) => row({ substance: a.substance, reaction: a.reaction, severity: a.severity, category: a.category ?? "medication" })),
    medications: item.medications.map((m) => row({
      name: m.name, dose: m.dose, route: m.route, frequency: m.frequency,
      indication: m.indication, adherence: m.adherence, accessCost: m.accessCost,
      isCompound: m.isCompound ? "true" : "false",
      compoundIngredients: m.compoundIngredients ?? "",
      compoundVehicle: m.compoundVehicle ?? "",
      compoundReason: m.compoundReason ?? "",
    })),
    problems: item.problems.map((p) => row({ code: p.code, description: p.description, since: p.since })),
    labs: item.labs.map((l) => row({
      name: l.name, value: l.value, unit: l.unit, referenceRange: l.referenceRange, flag: l.flag, collectedAt: l.collectedAt.slice(0, 10),
    })),
    vitals: item.vitals.map((v) => row({ label: v.label, value: v.value })),
    lungSounds: (item.lungSounds ?? []).map((s) => row({
      location: s.location, finding: s.finding, notes: s.notes ?? "",
    })),
    sectionLocks: { ...DEFAULT_LOCKS, ...(item.sectionLocks ?? {}) },
    prefillSections: item.prefillSections ?? [],
    unit: item.unit ?? "",
    room: item.room ?? "",
    bed: item.bed ?? "",
  };
}

export default function CaseEditorPage() {
  const { caseId = "new" } = useParams();
  const isNew = caseId === "new";
  const navigate = useNavigate();
  const { activeRole, courseId } = useSession();
  const existing = useAsync(() => (isNew ? Promise.resolve(undefined) : getCase(activeRole, caseId)), [isNew, caseId, activeRole]);
  const [draft, setDraft] = useState<Draft>(emptyDraft);
  const [error, setError] = useState("");
  const [photoMessage, setPhotoMessage] = useState("");
  const [busy, setBusy] = useState(false);
  const [loadedId, setLoadedId] = useState("");

  usePageHeading(isNew ? "New case" : "Edit case");

  if (existing.data && existing.data.id !== loadedId) {
    setLoadedId(existing.data.id);
    setDraft(draftFrom(existing.data));
  }

  const set = (patch: Partial<Draft>) => setDraft((current) => ({ ...current, ...patch }));

  const save = async (event: FormEvent) => {
    event.preventDefault();
    if (!draft.firstName.trim() || !draft.lastName.trim() || !draft.dob) {
      setError("First name, last name, and date of birth are required.");
      return;
    }
    const body: CaseInput = {
      firstName: draft.firstName.trim(),
      lastName: draft.lastName.trim(),
      preferredName: draft.preferredName.trim() || undefined,
      dob: draft.dob,
      sexAtBirth: draft.sexAtBirth,
      pronouns: draft.pronouns.trim() || undefined,
      chiefComplaint: draft.chiefComplaint,
      hpi: draft.hpi,
      pastMedicalHistory: draft.pastMedicalHistory,
      surgicalHistory: draft.surgicalHistory,
      familyHistory: draft.familyHistory,
      socialHistory: draft.socialHistory,
      insurancePayer: draft.insurancePayer.trim() || undefined,
      insuranceMemberId: draft.insuranceMemberId.trim() || undefined,
      insuranceGroupNumber: draft.insuranceGroupNumber.trim() || undefined,
      insuranceNotes: draft.insuranceNotes.trim() || undefined,
      emergencyContactName: draft.emergencyContactName.trim() || undefined,
      emergencyContactPhone: draft.emergencyContactPhone.trim() || undefined,
      emergencyContactRelationship: draft.emergencyContactRelationship.trim() || undefined,
      codeStatus: draft.codeStatus || undefined,
      advanceDirectiveNotes: draft.advanceDirectiveNotes.trim() || undefined,
      hipaaOnFile: draft.hipaaOnFile,
      hipaaNote: draft.hipaaNote.trim() || undefined,
      encounterType: draft.encounterType,
      careSetting: draft.careSetting,
      lifecycle: draft.lifecycle,
      encounterStatus: draft.encounterStatus,
      program: draft.program.trim() || undefined,
      allergies: draft.allergies.filter((r) => r.substance.trim()).map((r) => ({
        substance: r.substance, reaction: r.reaction || undefined, category: (r.category || "medication") as "medication" | "food" | "environmental",
        severity: (r.severity || undefined) as CaseInput["allergies"][number]["severity"],
      })),
      medications: draft.medications.filter((r) => r.name.trim()).map((r) => {
        const isCompound = r.isCompound === "true";
        return {
          name: r.name, dose: r.dose, route: r.route, frequency: r.frequency,
          indication: r.indication || undefined, adherence: r.adherence || undefined, accessCost: r.accessCost || undefined,
          isCompound,
          compoundIngredients: isCompound ? (r.compoundIngredients || undefined) : undefined,
          compoundVehicle: isCompound ? (r.compoundVehicle || undefined) : undefined,
          compoundReason: isCompound ? (r.compoundReason || undefined) : undefined,
        };
      }),
      problems: draft.problems.filter((r) => r.description.trim()).map((r) => ({
        code: r.code || undefined, description: r.description, since: r.since || undefined,
      })),
      labs: draft.labs.filter((r) => r.name.trim()).map((r) => ({
        name: r.name, value: r.value, unit: r.unit, referenceRange: r.referenceRange,
        flag: (r.flag || undefined) as "H" | "L" | undefined,
        collectedAt: r.collectedAt,
      })),
      vitals: draft.vitals.filter((r) => r.label.trim()).map((r) => ({ label: r.label, value: r.value })),
      lungSounds: draft.lungSounds.filter((r) => r.location.trim() && r.finding.trim()).map((r) => ({
        location: r.location,
        finding: r.finding,
        notes: r.notes.trim() || undefined,
      })),
      sectionLocks: draft.sectionLocks,
      prefillSections: draft.prefillSections,
      unit: draft.unit || undefined,
      room: draft.room || undefined,
      bed: draft.bed || undefined,
    };
    setBusy(true);
    setError("");
    try {
      const saved = isNew ? await createCase(activeRole, courseId, body) : await updateCase(activeRole, caseId, body);
      navigate(`/cases/${saved.id}`, { replace: true });
      if (!isNew) existing.reload();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  };

  const uploadPhoto = async (file?: File) => {
    if (!file || !existing.data) return;
    setError("");
    setPhotoMessage("");
    if (!["image/jpeg", "image/png", "image/webp"].includes(file.type)) {
      setError("Use a JPEG, PNG, or WebP photo.");
      return;
    }
    if (file.size > 1_000_000) {
      setError("The photo must be 1 MB or smaller.");
      return;
    }
    const bytes = new Uint8Array(await file.arrayBuffer());
    let binary = "";
    bytes.forEach((value) => { binary += String.fromCharCode(value); });
    try {
      await savePatientPhoto(activeRole, existing.data.id, file.type, btoa(binary));
      setPhotoMessage("Photo saved on this case. Charts already assigned keep the earlier photo.");
    } catch (e) {
      setError((e as Error).message);
    }
  };

  if (existing.error) return <PageError error={existing.error} />;
  if (!isNew && !existing.data) return <LinearProgress aria-label="Loading case" />;

  return (
    <Stack component="form" spacing={2.5} onSubmit={save}>
      <Breadcrumbs aria-label="Breadcrumb">
        <Link component={RouterLink} to="/cases" underline="hover">Cases</Link>
        <Typography color="text.primary">{isNew ? "New case" : `${draft.lastName}, ${draft.firstName}`}</Typography>
      </Breadcrumbs>
      <Typography variant="body2" color="text.secondary">
        {isNew ? "Students cannot see this master." : `${existing.data?.mrn}. Saving changes the master only. Assigned copies stay as they were.`}
      </Typography>
      {error && <Alert severity="error">{error}</Alert>}
      {photoMessage && <Alert severity="success">{photoMessage}</Alert>}
      {!isNew && (
        <Paper sx={{ p: { xs: 2, md: 2.5 } }}>
          <Typography component="h2" variant="h6" sx={{ mb: 1 }}>Patient photo</Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 1.5 }}>
            One JPEG, PNG, or WebP up to 1 MB. The chart shows initials when there is no photo.
          </Typography>
          <Button variant="outlined" component="label">
            Choose photo
            <input
              hidden type="file" accept="image/jpeg,image/png,image/webp"
              aria-label="Patient photo"
              onChange={(e) => { void uploadPhoto(e.target.files?.[0]); e.target.value = ""; }}
            />
          </Button>
        </Paper>
      )}

      <Paper sx={{ p: { xs: 2, md: 2.5 } }}>
        <Typography component="h2" variant="h6" sx={{ mb: 1.5 }}>Demographics</Typography>
        <Box sx={{ display: "grid", gap: 2, gridTemplateColumns: { xs: "1fr", sm: "1fr 1fr" } }}>
          <TextField label="First name" required value={draft.firstName} onChange={(e) => set({ firstName: e.target.value })} />
          <TextField label="Last name" required value={draft.lastName} onChange={(e) => set({ lastName: e.target.value })} />
          <TextField label="Preferred name" value={draft.preferredName} onChange={(e) => set({ preferredName: e.target.value })} />
          <TextField label="Date of birth" type="date" required value={draft.dob} onChange={(e) => set({ dob: e.target.value })} slotProps={{ inputLabel: { shrink: true } }} />
          <TextField select label="Sex at birth" value={draft.sexAtBirth} onChange={(e) => set({ sexAtBirth: e.target.value as Draft["sexAtBirth"] })}>
            <MenuItem value="Female">Female</MenuItem>
            <MenuItem value="Male">Male</MenuItem>
          </TextField>
          <TextField label="Pronouns" value={draft.pronouns} onChange={(e) => set({ pronouns: e.target.value })} />
          <TextField label="Discipline" value={draft.program} onChange={(e) => set({ program: e.target.value })} placeholder="Pharmacy" />
        </Box>
      </Paper>

      <Paper sx={{ p: { xs: 2, md: 2.5 } }}>
        <Typography component="h2" variant="h6" sx={{ mb: 1.5 }}>Story</Typography>
        <Stack spacing={2}>
          <TextField label="Chief complaint" value={draft.chiefComplaint} onChange={(e) => set({ chiefComplaint: e.target.value })} fullWidth />
          <TextField label="History of present illness" value={draft.hpi} onChange={(e) => set({ hpi: e.target.value })} fullWidth multiline minRows={3} />
          <TextField label="Past medical history" value={draft.pastMedicalHistory} onChange={(e) => set({ pastMedicalHistory: e.target.value })} fullWidth multiline minRows={2} />
          <TextField label="Surgical history" value={draft.surgicalHistory} onChange={(e) => set({ surgicalHistory: e.target.value })} fullWidth multiline minRows={2} />
          <TextField label="Family history" value={draft.familyHistory} onChange={(e) => set({ familyHistory: e.target.value })} fullWidth multiline minRows={2} />
          <TextField label="Social history" value={draft.socialHistory} onChange={(e) => set({ socialHistory: e.target.value })} fullWidth multiline minRows={2} />
        </Stack>
      </Paper>

      <Paper sx={{ p: { xs: 2, md: 2.5 } }}>
        <Typography component="h2" variant="h6" sx={{ mb: 1.5 }}>Insurance scenario</Typography>
        <Box sx={{ display: "grid", gap: 2, gridTemplateColumns: { xs: "1fr", sm: "1fr 1fr" } }}>
          <TextField label="Payer" value={draft.insurancePayer} onChange={(e) => set({ insurancePayer: e.target.value })} />
          <TextField label="Member ID" value={draft.insuranceMemberId} onChange={(e) => set({ insuranceMemberId: e.target.value })} />
          <TextField label="Group number" value={draft.insuranceGroupNumber} onChange={(e) => set({ insuranceGroupNumber: e.target.value })} />
          <TextField label="Insurance notes" value={draft.insuranceNotes} onChange={(e) => set({ insuranceNotes: e.target.value })} multiline minRows={2} />
        </Box>
      </Paper>

      <Paper sx={{ p: { xs: 2, md: 2.5 } }}>
        <Typography component="h2" variant="h6" sx={{ mb: 1.5 }}>Emergency contact</Typography>
        <Box sx={{ display: "grid", gap: 2, gridTemplateColumns: { xs: "1fr", sm: "1fr 1fr" } }}>
          <TextField label="Name" value={draft.emergencyContactName} onChange={(e) => set({ emergencyContactName: e.target.value })} />
          <TextField label="Relationship" value={draft.emergencyContactRelationship} onChange={(e) => set({ emergencyContactRelationship: e.target.value })} />
          <TextField label="Phone" value={draft.emergencyContactPhone} onChange={(e) => set({ emergencyContactPhone: e.target.value })} />
        </Box>
      </Paper>

      <Paper sx={{ p: { xs: 2, md: 2.5 } }}>
        <Typography component="h2" variant="h6" sx={{ mb: 1.5 }}>Directives & consent</Typography>
        <Box sx={{ display: "grid", gap: 2, gridTemplateColumns: { xs: "1fr", sm: "1fr 1fr" } }}>
          <TextField
            select
            label="Code status"
            value={draft.codeStatus}
            onChange={(e) => set({ codeStatus: e.target.value as Draft["codeStatus"] })}
          >
            {CODE_STATUS.map((item) => (
              <MenuItem key={item || "blank"} value={item}>{item || "Not set"}</MenuItem>
            ))}
          </TextField>
          <FormControlLabel
            control={
              <Checkbox
                checked={draft.hipaaOnFile}
                onChange={(e) => set({ hipaaOnFile: e.target.checked })}
              />
            }
            label="Simulated HIPAA on file"
          />
          <TextField
            label="Advance directive notes"
            value={draft.advanceDirectiveNotes}
            onChange={(e) => set({ advanceDirectiveNotes: e.target.value })}
            multiline
            minRows={2}
            sx={{ gridColumn: { sm: "1 / -1" } }}
          />
          <TextField
            label="HIPAA / consent note"
            value={draft.hipaaNote}
            onChange={(e) => set({ hipaaNote: e.target.value })}
            multiline
            minRows={2}
            sx={{ gridColumn: { sm: "1 / -1" } }}
          />
        </Box>
      </Paper>

      <Paper sx={{ p: { xs: 2, md: 2.5 } }}>
        <Typography component="h2" variant="h6" sx={{ mb: 1.5 }}>Encounter</Typography>
        <Box sx={{ display: "grid", gap: 2, gridTemplateColumns: { xs: "1fr", sm: "1fr 1fr" } }}>
          <TextField label="Encounter type" value={draft.encounterType} onChange={(e) => set({ encounterType: e.target.value })} />
          <TextField select label="Care setting" value={draft.careSetting} onChange={(e) => set({ careSetting: e.target.value as CareSetting })}>
            {SETTING.map((item) => <MenuItem key={item} value={item}>{item}</MenuItem>)}
          </TextField>
          <TextField select label="Lifecycle" value={draft.lifecycle} onChange={(e) => set({ lifecycle: e.target.value as LifecycleStatus })}>
            {LIFECYCLE.map((item) => <MenuItem key={item} value={item}>{item}</MenuItem>)}
          </TextField>
          <TextField select label="Visit status" value={draft.encounterStatus} onChange={(e) => set({ encounterStatus: e.target.value as EncounterStatus })}>
            {ENCOUNTER.map((item) => <MenuItem key={item} value={item}>{item}</MenuItem>)}
          </TextField>
        </Box>
      </Paper>

      <Paper sx={{ p: { xs: 2, md: 2.5 } }}>
        <Typography component="h2" variant="h6">What students can change</Typography>
        <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
          Checked sections stay open on charts assigned after you save. Charts already assigned keep the locks and prefill they had. Name, date of birth, and MRN always appear in the note header. Other note text is copied only for the sections you check below.
        </Typography>
        <Box sx={{ display: "flex", flexWrap: "wrap" }}>
          {STUDENT_SECTIONS.map(([id, label]) => (
            <FormControlLabel
              key={id}
              label={label}
              control={<Checkbox checked={!draft.sectionLocks[id]} onChange={(e) => set({ sectionLocks: { ...draft.sectionLocks, [id]: !e.target.checked } })} />}
            />
          ))}
        </Box>
        <Typography variant="subtitle2" sx={{ mt: 1 }}>Copy into a new note</Typography>
        <Box sx={{ display: "flex", flexWrap: "wrap" }}>
          {PREFILL.map(([id, label]) => (
            <FormControlLabel
              key={id}
              label={label}
              control={<Checkbox checked={draft.prefillSections.includes(id)} onChange={(e) => set({
                prefillSections: e.target.checked ? [...draft.prefillSections, id] : draft.prefillSections.filter((item) => item !== id),
              })} />}
            />
          ))}
        </Box>
        <Box sx={{ display: "grid", gap: 1.5, gridTemplateColumns: { sm: "1fr 1fr 1fr" }, mt: 1 }}>
          <TextField label="Unit" value={draft.unit} onChange={(e) => set({ unit: e.target.value })} />
          <TextField label="Room" value={draft.room} onChange={(e) => set({ room: e.target.value })} />
          <TextField label="Bed" value={draft.bed} onChange={(e) => set({ bed: e.target.value })} />
        </Box>
      </Paper>

      <Paper sx={{ p: { xs: 2, md: 2.5 }, overflowX: "auto" }}>
        <EditableTable
          label="Allergies" addLabel="allergy" rows={draft.allergies} onChange={(allergies) => set({ allergies })}
          blank={{ substance: "", reaction: "", severity: "", category: "medication" }}
          columns={[
            { key: "substance", label: "Substance" },
            { key: "category", label: "Category", type: "select", options: ["medication", "food", "environmental"] },
            { key: "reaction", label: "Reaction" },
            { key: "severity", label: "Severity", type: "select", options: ["mild", "moderate", "severe"] },
          ]}
        />
      </Paper>
      <Paper sx={{ p: { xs: 2, md: 2.5 }, overflowX: "auto" }}>
        <EditableTable
          label="Medications" addLabel="medication" rows={draft.medications} onChange={(medications) => set({ medications })}
          blank={{
            name: "", dose: "", route: "", frequency: "", indication: "", adherence: "", accessCost: "",
            isCompound: "false", compoundIngredients: "", compoundVehicle: "", compoundReason: "",
          }}
          columns={[
            { key: "name", label: "Name" }, { key: "dose", label: "Dose" }, { key: "route", label: "How taken" },
            { key: "frequency", label: "Frequency" }, { key: "adherence", label: "Adherence" },
            { key: "accessCost", label: "Access or cost" }, { key: "indication", label: "Indication" },
            { key: "isCompound", label: "Compound", type: "select", options: ["false", "true"] },
            { key: "compoundIngredients", label: "Ingredients" },
            { key: "compoundVehicle", label: "Vehicle" },
            { key: "compoundReason", label: "Why compounded" },
          ]}
        />
      </Paper>
      <Paper sx={{ p: { xs: 2, md: 2.5 }, overflowX: "auto" }}>
        <EditableTable
          label="Problems" addLabel="problem" rows={draft.problems} onChange={(problems) => set({ problems })}
          blank={{ code: "", description: "", since: "" }}
          columns={[{ key: "code", label: "Code" }, { key: "description", label: "Description" }, { key: "since", label: "Since" }]}
        />
      </Paper>
      <Paper sx={{ p: { xs: 2, md: 2.5 }, overflowX: "auto" }}>
        <EditableTable
          label="Labs" addLabel="lab" rows={draft.labs} onChange={(labs) => set({ labs })}
          blank={{ name: "", value: "", unit: "", referenceRange: "", flag: "", collectedAt: "" }}
          columns={[
            { key: "name", label: "Test" }, { key: "value", label: "Result" }, { key: "unit", label: "Unit" },
            { key: "referenceRange", label: "Range" },
            { key: "flag", label: "Flag", type: "select", options: ["H", "L"] },
            { key: "collectedAt", label: "Collected", type: "date" },
          ]}
        />
      </Paper>
      <Paper sx={{ p: { xs: 2, md: 2.5 }, overflowX: "auto" }}>
        <EditableTable
          label="Vitals" addLabel="vital" rows={draft.vitals} onChange={(vitals) => set({ vitals })}
          blank={{ label: "", value: "" }}
          columns={[{ key: "label", label: "Label" }, { key: "value", label: "Value" }]}
        />
      </Paper>
      <Paper sx={{ p: { xs: 2, md: 2.5 }, overflowX: "auto" }}>
        <EditableTable
          label="Lung sounds" addLabel="lung sound" rows={draft.lungSounds} onChange={(lungSounds) => set({ lungSounds })}
          blank={{ location: "RUL", finding: "clear", notes: "" }}
          columns={[
            { key: "location", label: "Location", type: "select", options: ["RUL", "RML", "RLL", "LUL", "LLL"] },
            { key: "finding", label: "Finding", type: "select", options: ["clear", "crackles", "wheeze", "diminished", "rhonchi", "other"] },
            { key: "notes", label: "Notes" },
          ]}
        />
      </Paper>

      {isNew ? (
        <Paper sx={{ p: { xs: 2, md: 2.5 } }}>
          <Typography component="h2" variant="h6">Answer key, rubric, and triggers</Typography>
          <Typography variant="body2" color="text.secondary">Save the case first. Then you can add the expected diagnoses, a rubric, and planted triggers.</Typography>
        </Paper>
      ) : (
        <>
          <Paper sx={{ p: { xs: 2, md: 2.5 } }}>
            <AnswerKeyEditor role={activeRole} caseId={caseId} />
          </Paper>
          <Paper sx={{ p: { xs: 2, md: 2.5 } }}>
            <CaseRubricPanel key={existing.data?.updatedAt ?? "new"} role={activeRole} caseId={caseId} initial={existing.data?.gradingGuide} />
          </Paper>
          <Paper sx={{ p: { xs: 2, md: 2.5 } }}>
            <CaseTriggersEditor key={existing.data?.updatedAt ?? "new"} role={activeRole} caseId={caseId} initial={existing.data?.triggers ?? []} />
          </Paper>
        </>
      )}

      <Box sx={{ display: "flex", gap: 1 }}>
        <Button type="submit" variant="contained" disabled={busy}>{isNew ? "Create case" : "Save case"}</Button>
        <Button type="button" onClick={() => navigate("/cases")}>Cancel</Button>
      </Box>
    </Stack>
  );
}
