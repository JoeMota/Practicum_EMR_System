import { useEffect, useState } from "react";
import { Autocomplete, Box, Button, Chip, InputAdornment, LinearProgress, Stack, TextField, Typography } from "@mui/material";
import type { IcdCode, NoteComment, NoteTemplateId, Patient } from "../../../types";
import { searchIcd10 } from "../../../api/reference";
import { listNoteTemplates } from "../../../api/templates";
import { useSession } from "../../auth/useSession";
import { useAsync } from "../../../utils/useAsync";
import { TEMPLATES, type NoteTemplate, type TemplateField } from "../noteTemplates";
import { legacyProse } from "../generalSoap";
import { AssessmentEditor, HpiEditor, NarrativeButton, ProblemPlanEditor, RosEditor } from "./GeneralSoapFields";
import DictationButton from "../../../components/DictationButton";
import MedRecTable from "./MedRecTable";
import { parseMedRec } from "./medRec";
import FeedbackThread from "./FeedbackThread";
import { utep } from "../../../theme/tokens";

type Setter = (id: string, next: string | ((prev: string) => string)) => void;

interface Props {
  templateId: string;
  patient: Patient;
  content: Record<string, string>;
  diagnoses: IcdCode[];
  readOnly?: boolean;
  errors?: Set<string>;
  onField?: Setter;
  onDiagnoses?: (d: IcdCode[]) => void;
  comments?: NoteComment[];
  onComment?: (sectionId: string, body: string) => Promise<void>;
  onFill?: (sectionId: string) => void;
}

const SOAP = new Set(["S", "O", "A", "P"]);

export default function NoteFields({
  templateId, patient, content, diagnoses, readOnly, errors, onField, onDiagnoses, comments, onComment, onFill,
}: Props) {
  const { activeRole, courseId } = useSession();
  const saved = useAsync(() => listNoteTemplates(activeRole, courseId), [activeRole, courseId]);
  const builtin: NoteTemplate | undefined = templateId in TEMPLATES ? TEMPLATES[templateId as NoteTemplateId] : undefined;
  const savedRow = (saved.data ?? []).find((row) => row.id === templateId);
  const template: NoteTemplate | undefined = builtin ?? (savedRow
    ? { id: savedRow.id, name: savedRow.name, disciplines: [savedRow.discipline], sections: savedRow.sections }
    : undefined);
  const [openSection, setOpenSection] = useState<string | null>(null);
  const [draft, setDraft] = useState("");
  const [sending, setSending] = useState(false);
  const [commentError, setCommentError] = useState("");

  if (!template && (saved.loading || !saved.data)) return <LinearProgress aria-label="Loading template" />;
  if (!template) return <Typography color="text.secondary">This template is no longer available.</Typography>;

  const send = async (sectionId: string) => {
    if (!onComment || !draft.trim()) return;
    setSending(true);
    setCommentError("");
    try {
      await onComment(sectionId, draft.trim());
      setDraft("");
      setOpenSection(null);
    } catch (e) {
      setCommentError((e as Error).message);
    } finally {
      setSending(false);
    }
  };

  return (
    <Stack spacing={0}>
      {template.sections.map((section, index) => {
        const sectionComments = (comments ?? []).filter((item) => item.sectionId === section.id);
        return (
        <Box
          component="section"
          key={section.id}
          aria-labelledby={`sec-${section.id}`}
          sx={{
            py: 2.75,
            borderTop: index === 0 ? "none" : `1px solid ${utep.lineSoft}`,
            "@keyframes noteSectionIn": {
              from: { opacity: 0, transform: "translateY(4px)" },
              to: { opacity: 1, transform: "none" },
            },
            animation: "noteSectionIn 220ms ease both",
            animationDelay: `${Math.min(index, 4) * 40}ms`,
            "@media (prefers-reduced-motion: reduce)": { animation: "none" },
          }}
        >
          <Box sx={{ display: "flex", alignItems: "center", gap: 1.25, mb: 1.5, flexWrap: "wrap" }}>
            {SOAP.has(section.id) && (
              <Box aria-hidden sx={{ width: 28, height: 28, borderRadius: 1, bgcolor: utep.navy, color: "#fff", display: "grid", placeItems: "center", fontWeight: 800, fontSize: 13 }}>
                {section.id}
              </Box>
            )}
            <Typography id={`sec-${section.id}`} component="h3" variant="h6" sx={{ flex: 1 }}>{section.title}</Typography>
            {onFill && !readOnly && (
              <Button size="small" onClick={() => onFill(section.id)} sx={{ minHeight: 44 }}>Fill from chart</Button>
            )}
            {onComment && (
              <Button type="button" size="small" onClick={() => { setOpenSection(section.id); setDraft(""); setCommentError(""); }}>
                Comment on this section
              </Button>
            )}
          </Box>
          {sectionComments.length > 0 && <Box sx={{ mb: 1.5 }}><FeedbackThread items={sectionComments} hideSection /></Box>}
          {onComment && openSection === section.id && (
            <Stack spacing={1} sx={{ mb: 1.5 }}>
              <TextField
                label={`Comment on ${section.title}`}
                value={draft}
                onChange={(e) => setDraft(e.target.value)}
                multiline
                minRows={2}
                fullWidth
              />
              {commentError && <Typography variant="body2" color="error">{commentError}</Typography>}
              <Box sx={{ display: "flex", gap: 1 }}>
                <Button type="button" variant="contained" size="small" disabled={sending || !draft.trim()} onClick={() => send(section.id)}>
                  Save comment
                </Button>
                <Button type="button" size="small" onClick={() => setOpenSection(null)}>Cancel</Button>
              </Box>
            </Stack>
          )}
          <Stack spacing={2}>
            {section.fields.map((f) => (
              <Field
                key={f.id} templateId={templateId} field={f} patient={patient} content={content} value={content[f.id] ?? ""} diagnoses={diagnoses}
                readOnly={readOnly} error={errors?.has(f.id)} onField={onField} onDiagnoses={onDiagnoses}
              />
            ))}
          </Stack>
        </Box>
        );
      })}
      {templateId === "general_soap" && <NarrativeButton patient={patient} content={content} diagnoses={diagnoses} />}
    </Stack>
  );
}

function Field({
  templateId, field: f, patient, content, value, diagnoses, readOnly, error, onField, onDiagnoses,
}: {
  templateId: string; field: TemplateField; patient: Patient; content: Record<string, string>; value: string; diagnoses: IcdCode[];
  readOnly?: boolean; error?: boolean; onField?: Setter; onDiagnoses?: (d: IcdCode[]) => void;
}) {
  const label = f.label;
  const structured = templateId === "general_soap";

  if (structured && f.id === "hpi") {
    return (
      <Stack spacing={1.5}>
        <HpiEditor content={content} readOnly={readOnly} onField={onField} />
        {readOnly ? <ReadBlock label="Additional HPI">{value ? <Typography variant="body2" sx={{ whiteSpace: "pre-wrap" }}>{value}</Typography> : null}</ReadBlock> : (
          <TextField label="Additional HPI" helperText="Free text is kept so older notes still show their history." fullWidth multiline minRows={3} value={value} onChange={(e) => onField?.(f.id, e.target.value)} />
        )}
      </Stack>
    );
  }

  if (structured && f.id === "ros") {
    const earlier = legacyProse(value);
    return (
      <Stack spacing={1.5}>
        {earlier && <ReadBlock label="Earlier review of systems"><Typography variant="body2" sx={{ whiteSpace: "pre-wrap" }}>{earlier}</Typography></ReadBlock>}
        <RosEditor content={content} readOnly={readOnly} onField={onField} />
      </Stack>
    );
  }

  if (structured && f.id === "plan") {
    const earlier = legacyProse(value);
    return (
      <Stack spacing={1.5}>
        {earlier && <ReadBlock label="Earlier plan text"><Typography variant="body2" sx={{ whiteSpace: "pre-wrap" }}>{earlier}</Typography></ReadBlock>}
        <ProblemPlanEditor content={content} diagnoses={diagnoses} readOnly={readOnly} onField={onField} />
      </Stack>
    );
  }

  if (f.kind === "medrec") {
    return (
      <MedRecTable
        medications={patient.medications} value={parseMedRec(value)} readOnly={readOnly}
        onChange={(v) => onField?.(f.id, JSON.stringify(v))}
      />
    );
  }

  if (f.kind === "icd10") {
    if (structured) return <AssessmentEditor diagnoses={diagnoses} readOnly={readOnly} onDiagnoses={onDiagnoses} chartDiagnoses={chartDiagnoses(patient)} />;
    if (readOnly) {
      return (
        <ReadBlock label={f.label}>
          {diagnoses.length ? diagnoses.map((d) => <Typography key={d.code} variant="body2"><b>{d.code}</b> {d.label}{d.rationale ? ` — ${d.rationale}` : ""}</Typography>) : null}
        </ReadBlock>
      );
    }
    return (
      <IcdSearch
        id={`field-${f.id}`} label={label} value={diagnoses} error={error}
        chartDiagnoses={chartDiagnoses(patient)}
        onChange={(next) => onDiagnoses?.(next)}
      />
    );
  }

  if (readOnly) {
    return <ReadBlock label={f.label}>{value ? <Typography variant="body2" sx={{ whiteSpace: "pre-wrap" }}>{value}</Typography> : null}</ReadBlock>;
  }

  return (
    <TextField
      id={`field-${f.id}`} label={label} placeholder={f.placeholder} fullWidth
      multiline={f.kind === "textarea"} minRows={f.kind === "textarea" ? f.rows ?? 3 : undefined}
      value={value} error={error}
      onChange={(e) => onField?.(f.id, e.target.value)}
      slotProps={f.kind === "textarea" ? { input: {
        endAdornment: (
          <InputAdornment position="end" sx={{ alignSelf: "flex-start", mt: 1 }}>
            <DictationButton label={f.label} onText={(t) => onField?.(f.id, (prev) => (prev ? `${prev} ${t}` : t))} />
          </InputAdornment>
        ),
      } } : undefined}
    />
  );
}

function chartDiagnoses(patient: Patient): IcdCode[] {
  return patient.problems.flatMap((problem) => problem.code ? [{ code: problem.code, label: problem.description }] : []);
}

function IcdSearch({
  id, label, value, error, onChange, chartDiagnoses: fromChart = [],
}: {
  id: string; label: string; value: IcdCode[]; error?: boolean; onChange: (next: IcdCode[]) => void; chartDiagnoses?: IcdCode[];
}) {
  const [options, setOptions] = useState<IcdCode[]>([]);
  const [query, setQuery] = useState("");
  const [lookupError, setLookupError] = useState("");

  const term = query.trim();
  const searching = term.length >= 2;
  useEffect(() => {
    if (!searching) return;
    let alive = true;
    const timer = setTimeout(() => {
      searchIcd10(term)
        .then((rows) => { if (alive) { setOptions(rows); setLookupError(""); } })
        .catch((e: Error) => { if (alive) { setOptions([]); setLookupError(e.message); } });
    }, 250);
    return () => { alive = false; clearTimeout(timer); };
  }, [term, searching]);

  return (
    <Autocomplete
      multiple options={searching ? [...fromChart, ...options.filter((row) => !fromChart.some((item) => item.code === row.code))] : fromChart} value={value} filterOptions={(rows) => rows}
      getOptionLabel={(option) => `${option.code} ${option.label}`}
      isOptionEqualToValue={(a, b) => a.code === b.code}
      onChange={(_, next) => onChange(next)}
      onInputChange={(_, next) => setQuery(next)}
      noOptionsText={query.trim().length < 2 ? "Type at least 2 characters" : "No matching ICD-10 codes"}
      renderValue={(selected, getItemProps) =>
        selected.map((option, index) => {
          const { key, ...rest } = getItemProps({ index });
          return <Chip key={key} {...rest} size="small" label={`${option.code} ${option.label}`} />;
        })
      }
      renderInput={(params) => (
        <TextField
          {...params} id={id} label={label}
          placeholder={value.length ? "" : "Search the ICD-10 catalog"}
          error={error || Boolean(lookupError)}
          helperText={lookupError || "Codes come from the NLM ICD-10-CM search. Primary diagnosis first — these codes also support teaching about coverage/billing."}
        />
      )}
    />
  );
}

function ReadBlock({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <Box>
      <Typography variant="subtitle2" color="text.secondary">{label}</Typography>
      {children ?? <Typography variant="body2" color="text.secondary" sx={{ fontStyle: "italic" }}>Not documented</Typography>}
    </Box>
  );
}
