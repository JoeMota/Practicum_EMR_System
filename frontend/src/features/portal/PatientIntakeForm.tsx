import { useState, type FormEvent, type ReactNode } from "react";
import {
  Alert, Box, Button, Checkbox, FormControlLabel, MenuItem, Paper, Stack, TextField, Typography,
} from "@mui/material";
import type { IntakeData, PortalIntake } from "../../api/intake";
import { savePortalIntake } from "../../api/intake";
import { formatDateTime } from "../../utils/format";
import {
  alcoholUseOptions, commonConditions, drugUseOptions, ethnicityOptions, genderIdentityOptions,
  insurancePlanTypeOptions, insuranceRelationshipOptions, maritalStatusOptions, phoneTypeOptions,
  preferredLanguageOptions, raceOptions, relativeOptions, relativeStatusOptions, tobaccoUseOptions,
} from "./intakeOptions";
import { toPayload, validateIntake } from "./intakeUtils";
import ListEditor from "./ListEditor";

const gridSx = { display: "grid", gap: 2, gridTemplateColumns: { xs: "1fr", sm: "1fr 1fr" } } as const;

type TextOptions = { multiline?: boolean; minRows?: number; type?: string; maxLength?: number };

interface Props {
  intake: PortalIntake;
  onSaved: (intake: PortalIntake) => void;
  previewMode?: boolean;
}

export default function PatientIntakeForm({ intake, onSaved, previewMode = false }: Props) {
  const [draft, setDraft] = useState<IntakeData>(intake.data);
  const [draftSource, setDraftSource] = useState(intake.data);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [saved, setSaved] = useState(false);
  if (draftSource !== intake.data) {
    setDraftSource(intake.data);
    setDraft(intake.data);
  }
  const errors = validateIntake(draft);
  const disabled = previewMode || !intake.editable;

  const update = (key: keyof IntakeData, value: unknown) => {
    setDraft((current) => ({ ...current, [key]: value }) as IntakeData);
    setError("");
    setSaved(false);
  };

  const textField = (label: string, key: keyof IntakeData, options: TextOptions = {}) => {
    const value = draft[key];
    if (typeof value !== "string") return null;
    const { maxLength, ...inputOptions } = options;
    const fieldError = errors[String(key)];
    return (
      <TextField
        label={label}
        value={value}
        disabled={disabled}
        error={Boolean(fieldError)}
        helperText={fieldError}
        onChange={(event) => update(key, event.target.value)}
        slotProps={maxLength ? { htmlInput: { maxLength } } : undefined}
        {...inputOptions}
      />
    );
  };

  const selectField = (label: string, key: keyof IntakeData, options: readonly string[]) => (
    <TextField
      select
      label={label}
      value={String(draft[key] ?? "")}
      disabled={disabled}
      onChange={(event) => update(key, event.target.value)}
    >
      {!options.includes("") && <MenuItem value="">Select</MenuItem>}
      {options.map((option) => <MenuItem key={option} value={option}>{option || "Select"}</MenuItem>)}
    </TextField>
  );

  const dateField = (label: string, key: "insuranceSubscriberDob" | "insuranceEffectiveDate") => (
    <TextField
      type="date"
      label={label}
      value={draft[key] ?? ""}
      disabled={disabled}
      slotProps={{ inputLabel: { shrink: true } }}
      onChange={(event) => update(key, event.target.value)}
    />
  );

  const setCondition = (name: string, checked: boolean) => {
    setDraft((current) => {
      const existing = current.conditions.find((item) => item.name === name);
      if (checked && !existing) return { ...current, conditions: [...current.conditions, { name, year: "" }] };
      if (!checked && existing) return { ...current, conditions: current.conditions.filter((item) => item.name !== name) };
      return current;
    });
    setError("");
    setSaved(false);
  };

  const save = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (Object.keys(errors).length) return;
    setBusy(true);
    setError("");
    setSaved(false);
    try {
      const result = await savePortalIntake(toPayload(draft));
      onSaved(result);
      setDraft(result.data);
      setSaved(true);
    } catch (cause) {
      setError((cause as Error).message);
    } finally {
      setBusy(false);
    }
  };

  const section = (title: string, content: ReactNode) => (
    <Paper sx={{ p: { xs: 2, md: 2.5 } }}>
      <Typography component="h2" variant="h6" sx={{ mb: 1.5 }}>{title}</Typography>
      {content}
    </Paper>
  );

  return (
    <Stack component="form" spacing={2.5} onSubmit={save}>
      {intake.source === "patient" && intake.updatedAt && !previewMode ? (
        <Alert severity="info">Your information was last updated {formatDateTime(intake.updatedAt)}. Review it and make any changes.</Alert>
      ) : !previewMode ? (
        <Alert severity="info">Review the information we have on file and complete anything missing.</Alert>
      ) : null}
      {!intake.editable && !previewMode && <Alert severity="info">{intake.notEditableReason}</Alert>}
      {error && <Alert severity="error">{error}</Alert>}
      {saved && <Alert severity="success">Saved.</Alert>}

      {section("Demographics", (
        <Box sx={gridSx}>
          <TextField label="Legal first name" value={intake.identity.firstName} disabled />
          <TextField label="Legal last name" value={intake.identity.lastName} disabled />
          <TextField label="Date of birth" type="date" value={intake.identity.dob} disabled slotProps={{ inputLabel: { shrink: true } }} />
          <TextField label="Sex at birth" value={intake.identity.sexAtBirth} disabled />
          <TextField label="MRN" value={intake.identity.mrn} disabled />
          {textField("Preferred name", "preferredName")}
          {textField("Pronouns", "pronouns")}
          {selectField("Gender identity", "genderIdentity", genderIdentityOptions)}
          <TextField
            select
            label="Race"
            value={draft.race}
            disabled={disabled}
            slotProps={{ select: { multiple: true } }}
            onChange={(event) => update("race", typeof event.target.value === "string" ? event.target.value.split(",") : event.target.value)}
          >
            {raceOptions.map((option) => <MenuItem key={option} value={option}>{option}</MenuItem>)}
          </TextField>
          {selectField("Ethnicity", "ethnicity", ethnicityOptions)}
          {selectField("Marital status", "maritalStatus", maritalStatusOptions)}
          {selectField("Preferred language", "preferredLanguage", preferredLanguageOptions)}
          <FormControlLabel
            control={<Checkbox checked={draft.interpreterNeeded} disabled={disabled} onChange={(event) => update("interpreterNeeded", event.target.checked)} />}
            label="I need an interpreter"
          />
        </Box>
      ))}

      {section("Contact", (
        <Box sx={gridSx}>
          {textField("Phone", "phone")}
          {selectField("Phone type", "phoneType", phoneTypeOptions)}
          {textField("Email", "email")}
          {textField("Street address", "address")}
          {textField("City", "city")}
          {textField("State", "state", { maxLength: 2 })}
          {textField("ZIP code", "zipCode")}
        </Box>
      ))}

      {section("Insurance", (
        <Stack spacing={2.5}>
          <Box sx={gridSx}>
            {textField("Primary carrier", "insurancePayer")}
            {selectField("Plan type", "insurancePlanType", insurancePlanTypeOptions)}
            {textField("Member ID", "insuranceMemberId")}
            {textField("Group number", "insuranceGroupNumber")}
            {dateField("Effective date", "insuranceEffectiveDate")}
            <FormControlLabel
              control={<Checkbox checked={draft.insuranceSubscriberIsPatient} disabled={disabled} onChange={(event) => update("insuranceSubscriberIsPatient", event.target.checked)} />}
              label="The patient is the subscriber"
            />
            {!draft.insuranceSubscriberIsPatient && <>
              {textField("Subscriber name", "insuranceSubscriberName")}
              {dateField("Subscriber date of birth", "insuranceSubscriberDob")}
              {selectField("Relationship to subscriber", "insuranceRelationship", insuranceRelationshipOptions)}
            </>}
          </Box>
          <Box>
            <Typography variant="subtitle2" sx={{ mb: 1.5 }}>Secondary insurance</Typography>
            <Box sx={gridSx}>
              {textField("Secondary carrier", "secondaryInsurancePayer")}
              {textField("Secondary member ID", "secondaryInsuranceMemberId")}
              {textField("Secondary group number", "secondaryInsuranceGroupNumber")}
              {selectField("Relationship to subscriber", "secondaryInsuranceRelationship", insuranceRelationshipOptions)}
            </Box>
          </Box>
        </Stack>
      ))}

      {section("Medical history", (
        <Stack spacing={2.5}>
          <Box>
            <Typography variant="subtitle2" sx={{ mb: 1 }}>Common conditions</Typography>
            <Box sx={{ display: "grid", gap: 0.5, gridTemplateColumns: { xs: "1fr", sm: "1fr 1fr" } }}>
              {commonConditions.map((name) => {
                const index = draft.conditions.findIndex((item) => item.name === name);
                const checked = index >= 0;
                const fieldError = checked ? errors[`conditions.${index}.year`] : undefined;
                return (
                  <Box key={name} sx={{ display: "grid", gap: 1, alignItems: "center", gridTemplateColumns: checked ? "minmax(0, 1fr) minmax(100px, 0.7fr)" : "1fr" }}>
                    <FormControlLabel
                      control={<Checkbox checked={checked} disabled={disabled} onChange={(event) => setCondition(name, event.target.checked)} />}
                      label={name}
                    />
                    {checked && (
                      <TextField
                        size="small"
                        label="Year diagnosed"
                        value={draft.conditions[index].year}
                        disabled={disabled}
                        error={Boolean(fieldError)}
                        helperText={fieldError}
                        onChange={(event) => {
                          setDraft((current) => ({ ...current, conditions: current.conditions.map((item, rowIndex) => rowIndex === index ? { ...item, year: event.target.value } : item) }));
                          setError("");
                          setSaved(false);
                        }}
                      />
                    )}
                  </Box>
                );
              })}
            </Box>
          </Box>
          {textField("Other conditions", "pastMedicalHistory", { multiline: true, minRows: 2 })}
          <ListEditor
            label="Surgeries"
            path="surgeries"
            rows={draft.surgeries}
            fields={[{ key: "procedure", label: "Procedure" }, { key: "year", label: "Year" }]}
            maxRows={20}
            disabled={disabled}
            createRow={() => ({ procedure: "", year: "" })}
            onChange={(rows) => update("surgeries", rows)}
            errorFor={(path) => errors[path]}
          />
          <ListEditor
            label="Allergies"
            path="allergies"
            rows={draft.allergies}
            fields={[{ key: "agent", label: "Allergen" }, { key: "reaction", label: "Reaction" }]}
            maxRows={20}
            disabled={disabled}
            createRow={() => ({ agent: "", reaction: "" })}
            onChange={(rows) => update("allergies", rows)}
          />
          <FormControlLabel
            control={<Checkbox checked={draft.noKnownAllergies} disabled={disabled} onChange={(event) => update("noKnownAllergies", event.target.checked)} />}
            label="No known allergies"
          />
          <ListEditor
            label="Medications"
            path="medications"
            rows={draft.medications}
            fields={[{ key: "name", label: "Medication" }, { key: "dose", label: "Dose" }, { key: "frequency", label: "Frequency" }]}
            maxRows={25}
            disabled={disabled}
            createRow={() => ({ name: "", dose: "", frequency: "" })}
            onChange={(rows) => update("medications", rows)}
          />
        </Stack>
      ))}

      {section("Family history", (
        <Stack spacing={2.5}>
          <ListEditor
            label="Family members"
            path="familyMembers"
            rows={draft.familyMembers}
            fields={[
              { key: "relative", label: "Relative", options: relativeOptions },
              { key: "status", label: "Status", options: relativeStatusOptions },
              { key: "conditions", label: "Conditions" },
            ]}
            maxRows={15}
            disabled={disabled}
            createRow={() => ({ relative: "Other", status: "", conditions: "" })}
            onChange={(rows) => update("familyMembers", rows)}
          />
          {textField("Other family history", "familyHistory", { multiline: true, minRows: 2 })}
        </Stack>
      ))}

      {section("Social history", (
        <Box sx={gridSx}>
          {selectField("Tobacco use", "tobaccoUse", tobaccoUseOptions)}
          {draft.tobaccoUse && draft.tobaccoUse !== "Never" && textField("Tobacco details", "tobaccoDetail")}
          {selectField("Alcohol use", "alcoholUse", alcoholUseOptions)}
          {draft.alcoholUse && draft.alcoholUse !== "None" && textField("Alcohol details", "alcoholDetail")}
          {selectField("Drug use", "drugUse", drugUseOptions)}
          {textField("Occupation", "occupation")}
          {textField("Lives with", "livesWith")}
          {textField("Exercise", "exercise")}
          {textField("Other notes on lifestyle", "socialHistory", { multiline: true, minRows: 2 })}
        </Box>
      ))}

      {section("Emergency contact and pharmacy", (
        <Box sx={gridSx}>
          {textField("Emergency contact name", "emergencyContactName")}
          {textField("Emergency contact phone", "emergencyContactPhone")}
          {textField("Relationship", "emergencyContactRelationship")}
          {textField("Preferred pharmacy", "preferredPharmacy")}
        </Box>
      ))}

      {section("Review and save", (
        <Stack spacing={1.5}>
          <FormControlLabel
            control={<Checkbox checked={draft.confirmedAccurate} disabled={disabled} onChange={(event) => update("confirmedAccurate", event.target.checked)} />}
            label="I confirm this information is accurate to the best of my knowledge"
          />
          {!previewMode && (
            <Button type="submit" variant="contained" disabled={disabled || busy || !draft.confirmedAccurate || Object.keys(errors).length > 0} sx={{ alignSelf: "flex-start" }}>
              {busy ? "Saving…" : "Save information"}
            </Button>
          )}
        </Stack>
      ))}
    </Stack>
  );
}
