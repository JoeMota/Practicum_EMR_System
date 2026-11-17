import { useEffect, useState } from "react";
import {
  Autocomplete, Box, Button, Dialog, DialogActions, DialogContent, DialogTitle, IconButton, Stack, TextField, ToggleButton, ToggleButtonGroup, Typography,
} from "@mui/material";
import ArrowUpwardOutlined from "@mui/icons-material/ArrowUpwardOutlined";
import ArrowDownwardOutlined from "@mui/icons-material/ArrowDownwardOutlined";
import type { IcdCode, Patient } from "../../../types";
import { searchIcd10 } from "../../../api/reference";
import {
  compileNarrative, focusRos, hpiMnemonic, hpiValues, OLDCARTS, planFor, problemPlans, rosChecks, rosMode, SCHOLAR_MAC, visibleRos,
  type HpiMnemonic, type ProblemPlan, type RosMode, type RosStatus,
} from "../generalSoap";

type Setter = (id: string, next: string | ((prev: string) => string)) => void;

export function HpiEditor({ content, readOnly, onField }: { content: Record<string, string>; readOnly?: boolean; onField?: Setter }) {
  const mnemonic = hpiMnemonic(content);
  const fields = mnemonic === "scholar_mac" ? SCHOLAR_MAC : OLDCARTS;
  const values = hpiValues(content, mnemonic);
  const storageKey = mnemonic === "scholar_mac" ? "hpi_scholar" : "hpi_oldcarts";

  return (
    <Stack spacing={1.5}>
      <Box sx={{ display: "flex", alignItems: "center", gap: 1, flexWrap: "wrap" }}>
        <Typography variant="subtitle2">Structured history</Typography>
        <ToggleButtonGroup
          exclusive
          size="small"
          value={mnemonic}
          disabled={readOnly}
          onChange={(_, next: HpiMnemonic | null) => { if (next) onField?.("hpi_mnemonic", next); }}
          aria-label="History mnemonic"
        >
          <ToggleButton value="oldcarts">OLDCARTS</ToggleButton>
          <ToggleButton value="scholar_mac">SCHOLAR-MAC</ToggleButton>
        </ToggleButtonGroup>
      </Box>
      <Box sx={{ display: "grid", gap: 1.5, gridTemplateColumns: { xs: "1fr", sm: "1fr 1fr" } }}>
        {fields.map((field) => (
          <TextField
            key={field.id}
            label={field.label}
            value={values[field.id] ?? ""}
            disabled={readOnly}
            onChange={(event) => onField?.(storageKey, JSON.stringify({ ...values, [field.id]: event.target.value }))}
          />
        ))}
      </Box>
    </Stack>
  );
}

export function RosEditor({ content, readOnly, onField }: { content: Record<string, string>; readOnly?: boolean; onField?: Setter }) {
  const mode = rosMode(content);
  const checks = rosChecks(content);
  const groups = visibleRos(mode);

  const setMode = (next: RosMode) => {
    const updated = next === "focused" ? focusRos(checks) : checks;
    onField?.("ros_mode", next);
    onField?.("ros_checks", JSON.stringify(updated));
  };

  const setItem = (id: string, status: RosStatus) => {
    onField?.("ros_checks", JSON.stringify({ ...checks, [id]: status }));
  };

  return (
    <Stack spacing={1.5}>
      <Box sx={{ display: "flex", alignItems: "center", gap: 1, flexWrap: "wrap" }}>
        <Typography variant="subtitle2">Review of systems</Typography>
        <ToggleButtonGroup
          exclusive
          size="small"
          value={mode}
          disabled={readOnly}
          onChange={(_, next: RosMode | null) => { if (next) setMode(next); }}
          aria-label="Review of systems length"
        >
          <ToggleButton value="full">Full</ToggleButton>
          <ToggleButton value="focused">Focused</ToggleButton>
        </ToggleButtonGroup>
      </Box>
      <Typography variant="caption" color="text.secondary">
        Each item is positive, negative, or not asked. Focused mode hides the longer list and marks those items not asked. This section can be left empty.
      </Typography>
      {groups.map((group) => (
        <Box key={group.id}>
          <Typography variant="subtitle2" sx={{ mb: 0.5 }}>{group.label}</Typography>
          <Stack spacing={0.5}>
            {group.items.map((item) => (
              <Box key={item.id} sx={{ display: "flex", alignItems: "center", gap: 1, flexWrap: "wrap" }}>
                <Typography variant="body2" sx={{ minWidth: 160 }}>{item.label}</Typography>
                <ToggleButtonGroup
                  exclusive
                  size="small"
                  value={checks[item.id] ?? "not_asked"}
                  disabled={readOnly}
                  onChange={(_, next: RosStatus | null) => { if (next) setItem(item.id, next); }}
                  aria-label={item.label}
                >
                  <ToggleButton value="positive">Positive</ToggleButton>
                  <ToggleButton value="negative">Negative</ToggleButton>
                  <ToggleButton value="not_asked">Not asked</ToggleButton>
                </ToggleButtonGroup>
              </Box>
            ))}
          </Stack>
        </Box>
      ))}
    </Stack>
  );
}

export function AssessmentEditor({
  diagnoses, readOnly, onDiagnoses, chartDiagnoses = [],
}: {
  diagnoses: IcdCode[];
  readOnly?: boolean;
  onDiagnoses?: (next: IcdCode[]) => void;
  chartDiagnoses?: IcdCode[];
}) {
  const [options, setOptions] = useState<IcdCode[]>([]);
  const [query, setQuery] = useState("");
  const [lookupError, setLookupError] = useState("");

  const term = query.trim();
  const searching = term.length >= 2 && !readOnly;
  useEffect(() => {
    if (!searching) return;
    let alive = true;
    const timer = setTimeout(() => {
      searchIcd10(term)
        .then((rows) => { if (alive) { setOptions(rows); setLookupError(""); } })
        .catch((error: Error) => { if (alive) { setOptions([]); setLookupError(error.message); } });
    }, 250);
    return () => { alive = false; clearTimeout(timer); };
  }, [term, searching]);
  const shownOptions = searching
    ? [...chartDiagnoses, ...options.filter((row) => !chartDiagnoses.some((item) => item.code === row.code))]
    : chartDiagnoses;

  const move = (index: number, delta: number) => {
    const target = index + delta;
    if (!onDiagnoses || target < 0 || target >= diagnoses.length) return;
    const next = diagnoses.slice();
    const [item] = next.splice(index, 1);
    next.splice(target, 0, item);
    onDiagnoses(next);
  };

  return (
    <Stack spacing={1.5}>
      <Typography variant="subtitle2">Problem list (ICD-10)</Typography>
      {!readOnly && (
        <Autocomplete
          options={shownOptions}
          filterOptions={(rows) => rows}
          getOptionLabel={(option) => `${option.code} ${option.label}`}
          onInputChange={(_, next) => setQuery(next)}
          onChange={(_, option) => {
            if (!option || diagnoses.some((item) => item.code === option.code)) return;
            onDiagnoses?.([...diagnoses, { code: option.code, label: option.label, rationale: "" }]);
            setQuery("");
          }}
          noOptionsText={query.trim().length < 2 ? "Type at least 2 characters" : "No matching ICD-10 codes"}
          renderInput={(params) => (
            <TextField {...params} label="Add an ICD-10 code" error={Boolean(lookupError)} helperText={lookupError || "Order is the order of this list. Primary problem first."} />
          )}
        />
      )}
      {diagnoses.length === 0 && <Typography variant="body2" color="text.secondary">No problems selected.</Typography>}
      {diagnoses.map((item, index) => (
        <Box key={item.code} sx={{ display: "grid", gap: 1, gridTemplateColumns: readOnly ? "1fr" : "auto 1fr", alignItems: "start" }}>
          {!readOnly && (
            <Stack>
              <IconButton aria-label={`Move ${item.code} up`} disabled={index === 0} onClick={() => move(index, -1)}><ArrowUpwardOutlined fontSize="small" /></IconButton>
              <IconButton aria-label={`Move ${item.code} down`} disabled={index === diagnoses.length - 1} onClick={() => move(index, 1)}><ArrowDownwardOutlined fontSize="small" /></IconButton>
            </Stack>
          )}
          <Stack spacing={1} sx={{ flex: 1 }}>
            <Typography variant="body2"><b>{index + 1}. {item.code}</b> {item.label}</Typography>
            <TextField
              label="Rationale"
              value={item.rationale ?? ""}
              disabled={readOnly}
              multiline
              minRows={2}
              onChange={(event) => onDiagnoses?.(diagnoses.map((row, i) => i === index ? { ...row, rationale: event.target.value } : row))}
            />
            {!readOnly && (
              <Button sx={{ alignSelf: "flex-start" }} onClick={() => onDiagnoses?.(diagnoses.filter((row) => row.code !== item.code))}>Remove</Button>
            )}
          </Stack>
        </Box>
      ))}
    </Stack>
  );
}

export function ProblemPlanEditor({
  content, diagnoses, readOnly, onField,
}: {
  content: Record<string, string>;
  diagnoses: IcdCode[];
  readOnly?: boolean;
  onField?: Setter;
}) {
  const plans = problemPlans(content);
  const write = (code: string, patch: Partial<ProblemPlan>) => {
    onField?.("problem_plans", JSON.stringify({ ...plans, [code]: { ...planFor(plans, code), ...patch } }));
  };

  if (diagnoses.length === 0) {
    return <Typography variant="body2" color="text.secondary">Add a problem in the assessment to give it a plan. An empty plan can still be submitted.</Typography>;
  }

  return (
    <Stack spacing={2}>
      <Typography variant="subtitle2">Plan by problem</Typography>
      {diagnoses.map((item, index) => {
        const plan = planFor(plans, item.code);
        return (
          <Box key={item.code} sx={{ p: 1.5, border: 1, borderColor: "divider", borderRadius: 1 }}>
            <Typography variant="subtitle2" sx={{ mb: 1 }}>{index + 1}. {item.code} {item.label}</Typography>
            <Stack spacing={1}>
              <TextField label="Medications" value={plan.medications} disabled={readOnly} multiline minRows={2} onChange={(event) => write(item.code, { medications: event.target.value })} />
              <TextField label="Education" value={plan.education} disabled={readOnly} multiline minRows={2} onChange={(event) => write(item.code, { education: event.target.value })} />
              <TextField label="Follow-up" value={plan.followUp} disabled={readOnly} multiline minRows={2} onChange={(event) => write(item.code, { followUp: event.target.value })} />
              <TextField label="Referrals" value={plan.referrals} disabled={readOnly} multiline minRows={2} onChange={(event) => write(item.code, { referrals: event.target.value })} />
            </Stack>
          </Box>
        );
      })}
    </Stack>
  );
}

export function NarrativeButton({ patient, content, diagnoses }: { patient: Patient; content: Record<string, string>; diagnoses: IcdCode[] }) {
  const [open, setOpen] = useState(false);
  const narrative = compileNarrative(patient, content, diagnoses);

  return (
    <>
      <Button variant="outlined" onClick={() => setOpen(true)}>Compile narrative</Button>
      <Dialog open={open} onClose={() => setOpen(false)} fullWidth maxWidth="md">
        <DialogTitle>Compiled narrative</DialogTitle>
        <DialogContent>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 1.5 }}>
            Read-only preview from the structured fields, chief complaint, vitals, and free-text sections. It does not replace those fields and it is not saved as another note.
          </Typography>
          <Typography component="pre" variant="body2" sx={{ whiteSpace: "pre-wrap", fontFamily: "inherit" }}>{narrative}</Typography>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setOpen(false)}>Close</Button>
        </DialogActions>
      </Dialog>
    </>
  );
}
