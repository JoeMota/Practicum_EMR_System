import { useEffect, useState } from "react";
import {
  Alert, Autocomplete, Box, Button, IconButton, Stack, TextField, Typography,
} from "@mui/material";
import ArrowUpwardOutlined from "@mui/icons-material/ArrowUpwardOutlined";
import ArrowDownwardOutlined from "@mui/icons-material/ArrowDownwardOutlined";
import DeleteOutlined from "@mui/icons-material/DeleteOutlined";
import { getAnswerKey, putAnswerKey, type AnswerKey } from "../../api/cases";
import { listCpt } from "../../api/reference";
import { ICD10 } from "../encounters/icd10";
import { useAsync } from "../../utils/useAsync";
import type { IcdCode, Role } from "../../types";

interface DiagnosisRow {
  id: string;
  code: string;
  label: string;
  rationale: string;
}

function fromKey(key: AnswerKey): { rows: DiagnosisRow[]; expectedCptCodes: IcdCode[]; points: string[] } {
  return {
    rows: key.diagnoses.map((item) => ({
      id: crypto.randomUUID(),
      code: item.code,
      label: item.label,
      rationale: item.rationale,
    })),
    expectedCptCodes: key.expectedCptCodes ?? [],
    points: key.planPoints.length ? key.planPoints : [""],
  };
}

export default function AnswerKeyEditor({ role, caseId }: { role: Role; caseId: string }) {
  const loaded = useAsync(() => getAnswerKey(role, caseId), [role, caseId]);
  const [rows, setRows] = useState<DiagnosisRow[]>([]);
  const [points, setPoints] = useState<string[]>([""]);
  const [expectedCptCodes, setExpectedCptCodes] = useState<IcdCode[]>([]);
  const [cptOptions, setCptOptions] = useState<IcdCode[]>([]);
  const [rationale, setRationale] = useState("");
  const [hydratedFor, setHydratedFor] = useState("");
  const [error, setError] = useState("");
  const [saved, setSaved] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    listCpt().then(setCptOptions).catch(() => setCptOptions([]));
  }, []);

  if (loaded.data && hydratedFor !== caseId) {
    const next = fromKey(loaded.data);
    setHydratedFor(caseId);
    setRows(next.rows);
    setExpectedCptCodes(next.expectedCptCodes);
    setPoints(next.points);
    setRationale(loaded.data.rationale);
  }

  const move = (index: number, delta: number) => {
    const target = index + delta;
    if (target < 0 || target >= rows.length) return;
    const copy = rows.slice();
    const [item] = copy.splice(index, 1);
    copy.splice(target, 0, item);
    setRows(copy);
  };

  const save = async () => {
    setBusy(true);
    setError("");
    setSaved("");
    try {
      const key = await putAnswerKey(role, caseId, {
        diagnoses: rows.filter((row) => row.code && row.label).map((row, index) => ({
          rank: index + 1,
          code: row.code,
          label: row.label,
          rationale: row.rationale,
        })),
        planPoints: points.map((point) => point.trim()).filter(Boolean),
        expectedCptCodes,
        rationale,
      });
      const next = fromKey(key);
      setRows(next.rows);
      setExpectedCptCodes(next.expectedCptCodes);
      setPoints(next.points);
      setRationale(key.rationale);
      setSaved("Answer key saved. Students still cannot see it.");
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  };

  if (loaded.error) return <Alert severity="error">{loaded.error.message}</Alert>;
  if (!loaded.data) return null;

  return (
    <Stack spacing={2}>
      <Box>
        <Typography component="h2" variant="h6">Answer key</Typography>
        <Typography variant="body2" color="text.secondary">
          Expected diagnoses, in the order a strong note would list them. Students never receive this.
        </Typography>
      </Box>
      {error && <Alert severity="error">{error}</Alert>}
      {saved && <Alert severity="success">{saved}</Alert>}

      <Stack spacing={1.5}>
        {rows.map((row, index) => {
          const current: IcdCode | null = row.code ? { code: row.code, label: row.label } : null;
          const options = current && !ICD10.some((item) => item.code === current.code) ? [current, ...ICD10] : ICD10;
          return (
            <Box key={row.id} sx={{ display: "grid", gap: 1, gridTemplateColumns: { xs: "1fr", md: "auto 1fr" } }}>
              <Stack direction="row" spacing={0.5} sx={{ alignItems: "center" }}>
                <Typography variant="body2" sx={{ width: 24, fontWeight: 700 }}>{index + 1}</Typography>
                <IconButton type="button" aria-label="Move diagnosis up" disabled={index === 0} onClick={() => move(index, -1)} size="small">
                  <ArrowUpwardOutlined fontSize="small" />
                </IconButton>
                <IconButton type="button" aria-label="Move diagnosis down" disabled={index === rows.length - 1} onClick={() => move(index, 1)} size="small">
                  <ArrowDownwardOutlined fontSize="small" />
                </IconButton>
              </Stack>
              <Stack spacing={1}>
                <Autocomplete
                  options={options}
                  value={current}
                  getOptionLabel={(option) => `${option.code} ${option.label}`}
                  isOptionEqualToValue={(a, b) => a.code === b.code}
                  onChange={(_, value) => setRows(rows.map((item, i) => i === index ? { ...item, code: value?.code ?? "", label: value?.label ?? "" } : item))}
                  renderInput={(params) => <TextField {...params} label="ICD-10 code" placeholder="Search by code or condition" />}
                />
                <TextField
                  label="Why this diagnosis"
                  value={row.rationale}
                  onChange={(e) => setRows(rows.map((item, i) => i === index ? { ...item, rationale: e.target.value } : item))}
                  fullWidth
                  multiline
                  minRows={2}
                />
                <Box>
                  <Button
                    type="button"
                    color="inherit"
                    size="small"
                    startIcon={<DeleteOutlined />}
                    onClick={() => setRows(rows.filter((item) => item.id !== row.id))}
                  >
                    Remove diagnosis
                  </Button>
                </Box>
              </Stack>
            </Box>
          );
        })}
        <Box>
          <Button type="button" onClick={() => setRows([...rows, { id: crypto.randomUUID(), code: "", label: "", rationale: "" }])}>
            Add diagnosis
          </Button>
        </Box>
      </Stack>

      <Autocomplete
        multiple
        options={[
          ...expectedCptCodes.filter((current) => !cptOptions.some((option) => option.code === current.code)),
          ...cptOptions,
        ]}
        value={expectedCptCodes}
        getOptionLabel={(option) => `${option.code} ${option.label}`}
        isOptionEqualToValue={(option, value) => option.code === value.code}
        onChange={(_, value) => setExpectedCptCodes(value)}
        renderInput={(params) => <TextField {...params} label="Expected CPT codes" placeholder="Search CPT codes" />}
      />

      <Box>
        <Typography component="h3" variant="subtitle1" sx={{ fontWeight: 700, mb: 1 }}>Plan points</Typography>
        <Stack spacing={1}>
          {points.map((point, index) => (
            <Stack key={index} direction="row" spacing={1}>
              <TextField
                label={`Plan point ${index + 1}`}
                value={point}
                onChange={(e) => setPoints(points.map((item, i) => i === index ? e.target.value : item))}
                fullWidth
              />
              <IconButton type="button" aria-label="Remove plan point" onClick={() => setPoints(points.filter((_, i) => i !== index))} disabled={points.length === 1 && point === ""}>
                <DeleteOutlined />
              </IconButton>
            </Stack>
          ))}
          <Box>
            <Button type="button" onClick={() => setPoints([...points, ""])}>Add plan point</Button>
          </Box>
        </Stack>
      </Box>

      <TextField
        label="Overall rationale"
        value={rationale}
        onChange={(e) => setRationale(e.target.value)}
        fullWidth
        multiline
        minRows={3}
      />
      <Box>
        <Button type="button" variant="contained" disabled={busy} onClick={save}>Save answer key</Button>
      </Box>
    </Stack>
  );
}
