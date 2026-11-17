import { useEffect, useState } from "react";
import {
  Alert, Autocomplete, Box, Button, Checkbox, FormControlLabel, Paper, Stack, Table, TableBody, TableCell, TableHead, TableRow, TextField, Typography,
} from "@mui/material";
import type { Medication, Patient } from "../../types";
import {
  addMedication, administerMedication, deleteMedicationEnteredInError, discontinueMedication,
  listAdministrations, listMedicationOrders, reviewAdministration, reviewMedicationOrder,
  submitMedicationOrder, updateMedication, type AdministrationRecord, type MedicationOrderRecord,
} from "../../api/chart";
import { getCourse } from "../../api/courses";
import { lexicompInteractions, lexicompStatus, medicationDetails, searchMedications, type LexicompInteractions, type LexicompStatus } from "../../api/reference";
import { useSession } from "../auth/useSession";
import { can } from "../../utils/permissions";
import { canEditSection } from "../chart/access";
import { medicationSig } from "../../utils/sig";
import { useAsync } from "../../utils/useAsync";
import EmptyState from "../../components/EmptyState";

const blank = {
  name: "", dose: "", route: "", frequency: "", indication: "", adherence: "", accessCost: "", prescribed: false,
  isCompound: false, compoundIngredients: "", compoundVehicle: "", compoundReason: "",
  rxcui: "", genericName: "", brandNames: [] as string[], acknowledgedFlags: [] as string[],
};

export default function MedicationsTab({ patient, onChange }: { patient: Patient; onChange: (patient: Patient) => void }) {
  const { activeRole, courseId } = useSession();
  const course = useAsync(() => (courseId ? getCourse(courseId) : Promise.resolve(undefined)), [courseId]);
  const editable = canEditSection(activeRole, patient, "medications");
  const [form, setForm] = useState(blank);
  const [editingId, setEditingId] = useState<string>();
  const [names, setNames] = useState<string[]>([]);
  const [catalog, setCatalog] = useState<Record<string, string>>({});
  const [lexicomp, setLexicomp] = useState<LexicompStatus>();
  const [interactions, setInteractions] = useState<LexicompInteractions>();
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const given = useAsync(() => listAdministrations(activeRole, patient.id), [activeRole, patient.id]);
  const orders = useAsync(() => listMedicationOrders(activeRole, patient.id), [activeRole, patient.id]);
  const canReview = can(activeRole, "note:cosign");
  const canVerify =
    can(activeRole, "note:cosign")
    || can(activeRole, "case:author")
    || (patient.mode === "simulation" && patient.viewerStation === "pharmacist");
  const canSubmitOrder =
    editable
    || (patient.mode === "simulation" && Boolean(patient.viewerStation) && patient.simulationPhase !== "closed");
  const active = patient.medications.filter((item) => item.status !== "discontinued");
  const discontinued = patient.medications.filter((item) => item.status === "discontinued");
  const pendingIds = new Set((orders.data ?? []).filter((row) => row.status === "pending_verify").map((row) => row.medicationId));

  useEffect(() => {
    lexicompStatus().then(setLexicomp).catch((e: Error) => setLexicomp({ configured: false, detail: e.message }));
  }, []);

  const medicationNames = active.map((item) => item.name).join("|");
  useEffect(() => {
    let alive = true;
    lexicompInteractions(medicationNames ? medicationNames.split("|") : [])
      .then((result) => { if (alive) setInteractions(result); })
      .catch(() => { if (alive) setInteractions({ configured: false, text: null }); });
    return () => { alive = false; };
  }, [medicationNames]);

  useEffect(() => {
    const term = form.name.trim();
    if (term.length < 2) return;
    const timer = setTimeout(() => {
      searchMedications(term).then((rows) => {
        setNames(rows.map((row) => row.name));
        setCatalog(Object.fromEntries(rows.map((row) => [row.name.toLowerCase(), row.rxcui])));
      }).catch(() => setNames([]));
    }, 250);
    return () => clearTimeout(timer);
  }, [form.name]);

  useEffect(() => {
    const rxcui = catalog[form.name.trim().toLowerCase()];
    if (!rxcui || rxcui === form.rxcui) return;
    let alive = true;
    medicationDetails(rxcui)
      .then((detail) => {
        if (!alive) return;
        setForm((prev) => ({
          ...prev,
          rxcui: detail.rxcui,
          genericName: detail.genericName,
          brandNames: detail.brandNames,
        }));
      })
      .catch(() => undefined);
    return () => { alive = false; };
  }, [catalog, form.name, form.rxcui]);

  const needsAck = (course.data?.guardrailMode ?? (course.data?.guardrailProfile === "intro_pharmacy" ? "acknowledge" : "advisory")) === "acknowledge";

  const save = async () => {
    setError("");
    try {
      const body = {
        ...form,
        indication: form.indication || undefined,
        adherence: form.adherence || undefined,
        accessCost: form.accessCost || undefined,
        isCompound: form.isCompound,
        compoundIngredients: form.isCompound ? (form.compoundIngredients || undefined) : undefined,
        compoundVehicle: form.isCompound ? (form.compoundVehicle || undefined) : undefined,
        compoundReason: form.isCompound ? (form.compoundReason || undefined) : undefined,
        rxcui: form.rxcui || undefined,
        genericName: form.genericName || undefined,
        brandNames: form.brandNames,
        acknowledgedFlags: form.acknowledgedFlags,
      };
      const next = editingId
        ? await updateMedication(activeRole, patient.id, editingId, body)
        : await addMedication(activeRole, patient.id, body);
      onChange(next);
      setForm(blank);
      setEditingId(undefined);
    } catch (e) {
      setError((e as Error).message);
    }
  };

  const run = async (action: () => Promise<Patient | { status: string }>, notice?: string) => {
    setError("");
    try {
      const result = await action();
      if ("medications" in result) onChange(result);
      if (notice) setMessage(notice);
    } catch (e) {
      setError((e as Error).message);
    }
  };

  const pendingCount = (orders.data ?? []).filter((row) => row.status === "pending_verify").length;

  return (
    <Stack spacing={2}>
      {(canVerify || canSubmitOrder) && (
        <Alert severity="info">
          {canVerify
            ? `Fill verification is on this tab${pendingCount ? ` (${pendingCount} pending)` : ""}. Check allergies and compound notes, then verify, hold, or release.`
            : "Use Submit for verify on an active medication to send a fill to the pharmacist or instructor."}
        </Alert>
      )}
      {(interactions?.text || lexicomp?.url) && (
      <Paper sx={{ p: 2, borderRadius: "16px" }}>
        <Typography component="h2" variant="h6">Interaction checking</Typography>
        {interactions?.text && (
          <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>{interactions.text}</Typography>
        )}
        {lexicomp?.url && (
          <Button sx={{ mt: 1 }} href={lexicomp.url} target="_blank" rel="noreferrer">Open Lexicomp</Button>
        )}
      </Paper>
      )}
      {message && <Alert severity="info" onClose={() => setMessage("")}>{message}</Alert>}
      {error && <Alert severity="error" onClose={() => setError("")}>{error}</Alert>}
      {editable && (
        <Paper sx={{ p: 2, borderRadius: "16px" }}>
          <Typography component="h2" variant="h6" sx={{ mb: 1.5 }}>{editingId ? "Update medication" : "Add medication"}</Typography>
          <Box sx={{ display: "grid", gap: 1.5, gridTemplateColumns: { xs: "1fr", sm: "1fr 1fr 1fr" } }}>
            <Autocomplete
              freeSolo options={names} inputValue={form.name}
              onInputChange={(_, value) => setForm({ ...form, name: value })}
              renderInput={(params) => (
                <TextField
                  {...params}
                  label="Name"
                  helperText={
                    form.genericName
                      ? `Generic: ${form.genericName}${form.brandNames.length ? `. Brands: ${form.brandNames.slice(0, 3).join(", ")}` : ""}`
                      : "Names come from RxNorm. The Lexicomp catalog is separate."
                  }
                />
              )}
            />
            <TextField label="Dose" value={form.dose} onChange={(e) => setForm({ ...form, dose: e.target.value })} />
            <TextField label="How taken" value={form.route} onChange={(e) => setForm({ ...form, route: e.target.value })} />
            <TextField label="Frequency" value={form.frequency} onChange={(e) => setForm({ ...form, frequency: e.target.value })} />
            <TextField
              label="SIG preview"
              value={medicationSig(form.dose, form.route, form.frequency)}
              slotProps={{ input: { readOnly: true } }}
              helperText="Built from dose, route, and frequency"
            />
            <TextField label="Adherence" value={form.adherence} onChange={(e) => setForm({ ...form, adherence: e.target.value })} />
            <TextField label="Access or cost" value={form.accessCost} onChange={(e) => setForm({ ...form, accessCost: e.target.value })} />
            <TextField label="Indication" value={form.indication} onChange={(e) => setForm({ ...form, indication: e.target.value })} />
            <FormControlLabel
              control={<Checkbox checked={form.isCompound} onChange={(e) => setForm({ ...form, isCompound: e.target.checked })} />}
              label="Compounded medication"
            />
          </Box>
          {form.isCompound && (
            <Box sx={{ display: "grid", gap: 1.5, gridTemplateColumns: { xs: "1fr", sm: "1fr 1fr" }, mt: 1.5 }}>
              <TextField
                label="Ingredients"
                value={form.compoundIngredients}
                onChange={(e) => setForm({ ...form, compoundIngredients: e.target.value })}
                multiline minRows={2}
              />
              <TextField
                label="Vehicle / base"
                value={form.compoundVehicle}
                onChange={(e) => setForm({ ...form, compoundVehicle: e.target.value })}
              />
              <TextField
                label="Why compounded"
                value={form.compoundReason}
                onChange={(e) => setForm({ ...form, compoundReason: e.target.value })}
                multiline minRows={2}
                sx={{ gridColumn: { sm: "1 / -1" } }}
              />
            </Box>
          )}
          {needsAck && (
            <Button sx={{ mt: 1 }} size="small" onClick={() => setForm({ ...form, acknowledgedFlags: ["dose_extreme", "unit_mismatch", "missing_unit"] })}>
              I reviewed the dose warning
            </Button>
          )}
          <Button sx={{ mt: 1.5, minHeight: 44 }} variant="contained" onClick={save}>{editingId ? "Save change" : "Add medication"}</Button>
        </Paper>
      )}
      <MedTable
        title="Active medications"
        rows={active}
        empty="No active medications"
        editable={editable}
        inpatient={patient.status.careSetting === "Inpatient" && activeRole === "student"}
        pendingIds={pendingIds}
        canSubmitOrder={canSubmitOrder}
        onEdit={(row) => {
          setEditingId(row.id);
          setForm({
            name: row.name, dose: row.dose, route: row.route, frequency: row.frequency,
            indication: row.indication ?? "", adherence: row.adherence ?? "", accessCost: row.accessCost ?? "",
            prescribed: Boolean(row.prescribed),
            isCompound: Boolean(row.isCompound),
            compoundIngredients: row.compoundIngredients ?? "",
            compoundVehicle: row.compoundVehicle ?? "",
            compoundReason: row.compoundReason ?? "",
            rxcui: row.rxcui ?? "", genericName: row.genericName ?? "", brandNames: row.brandNames ?? [],
            acknowledgedFlags: [],
          });
        }}
        onDiscontinue={(row) => run(() => discontinueMedication(activeRole, patient.id, row.id!))}
        onMistake={(row) => run(() => deleteMedicationEnteredInError(activeRole, patient.id, row.id!))}
        onClear={canReview ? (row) => run(() => updateMedication(activeRole, patient.id, row.id!, { ...row, clearFlags: true })) : undefined}
        onSubmitOrder={(row) => run(
          async () => {
            await submitMedicationOrder(activeRole, patient.id, row.id!);
            orders.reload();
            return patient;
          },
          `${row.name} was submitted for pharmacist verification.`,
        )}
        onGive={(row) => run(
          () => administerMedication(activeRole, patient.id, row.id!, row.dose),
          `${row.name} was recorded and sent to the instructor for review.`,
        ).then(() => given.reload())}
      />
      <VerificationQueue
        rows={orders.data ?? []}
        allergies={patient.allergies}
        canVerify={canVerify}
        canResubmit={canSubmitOrder}
        onReview={async (row, decision) => {
          setError("");
          try {
            await reviewMedicationOrder(activeRole, row.id, decision, "");
            setMessage(
              decision === "verify" ? `${row.name} verified.`
                : decision === "hold" ? `${row.name} held for follow-up.`
                  : decision === "release" ? `${row.name} released.`
                    : `${row.name} resubmitted for verification.`,
            );
            orders.reload();
          } catch (e) {
            setError((e as Error).message);
          }
        }}
      />
      <AdministrationList
        rows={given.data ?? []}
        canReview={canReview}
        onReview={async (row, decision) => {
          await reviewAdministration(activeRole, row.id, decision, "");
          given.reload();
        }}
      />
      {discontinued.length > 0 && <MedTable title="Discontinued" rows={discontinued} empty="" editable={false} inpatient={false} />}
    </Stack>
  );
}

function AdministrationList({
  rows, canReview, onReview,
}: {
  rows: AdministrationRecord[];
  canReview: boolean;
  onReview: (row: AdministrationRecord, decision: "accepted" | "needs_follow_up") => Promise<void>;
}) {
  if (rows.length === 0) return null;
  return (
    <Paper sx={{ p: 2, borderRadius: "16px" }}>
      <Typography component="h2" variant="h6" sx={{ mb: 1 }}>Administration review</Typography>
      <Stack spacing={1}>
        {rows.map((row) => (
          <Box key={row.id}>
            <Typography variant="body2">
              <b>{row.medicationName}</b> {row.doseGiven} · {row.studentName} · {row.reviewStatus.replaceAll("_", " ")}
            </Typography>
            {canReview && row.reviewStatus === "pending_review" && (
              <Box>
                <Button size="small" onClick={() => onReview(row, "accepted")}>Accept</Button>
                <Button size="small" color="warning" onClick={() => onReview(row, "needs_follow_up")}>Needs follow-up</Button>
              </Box>
            )}
          </Box>
        ))}
      </Stack>
    </Paper>
  );
}

function VerificationQueue({
  rows, allergies, canVerify, canResubmit, onReview,
}: {
  rows: MedicationOrderRecord[];
  allergies: Patient["allergies"];
  canVerify: boolean;
  canResubmit: boolean;
  onReview: (row: MedicationOrderRecord, decision: "verify" | "hold" | "release" | "resubmit") => Promise<void>;
}) {
  if (rows.length === 0) return null;
  return (
    <Paper sx={{ p: 2, borderRadius: "16px" }}>
      <Typography component="h2" variant="h6">Fill verification</Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
        Submit → pharmacist verifies or holds → release. Check allergies before verifying.
      </Typography>
      {allergies.length > 0 && (
        <Alert severity="warning" sx={{ mt: 1.5 }}>
          Allergies: {allergies.map((item) => item.reaction ? `${item.substance} (${item.reaction})` : item.substance).join("; ")}
        </Alert>
      )}
      <Stack spacing={1.5} sx={{ mt: 1.5 }}>
        {rows.map((row) => (
          <Box key={row.id} sx={{ p: 1.5, borderRadius: "12px", bgcolor: "action.hover" }}>
            <Typography variant="body2">
              <b>{row.name}</b>
              {row.isCompound ? " · compounded" : ""}
              {" · "}
              <Box component="span" sx={{ fontFamily: "ui-monospace, SFMono-Regular, Menlo, monospace" }}>
                {row.sig || medicationSig(row.dose, row.route, row.frequency)}
              </Box>
              {row.quantity ? ` · qty ${row.quantity}` : ""}
            </Typography>
            <Typography variant="caption" color="text.secondary" sx={{ display: "block" }}>
              {row.status.replaceAll("_", " ")} · submitted by {row.submittedByName}
              {row.reviewedByName ? ` · reviewed by ${row.reviewedByName}` : ""}
              {row.reviewComment ? ` · ${row.reviewComment}` : ""}
            </Typography>
            <Box sx={{ mt: 0.5 }}>
              {canVerify && row.status === "pending_verify" && (
                <>
                  <Button size="small" onClick={() => onReview(row, "verify")}>Verify</Button>
                  <Button size="small" color="warning" onClick={() => onReview(row, "hold")}>Hold</Button>
                </>
              )}
              {canVerify && row.status === "verified" && (
                <Button size="small" onClick={() => onReview(row, "release")}>Release</Button>
              )}
              {canResubmit && row.status === "held" && (
                <Button size="small" onClick={() => onReview(row, "resubmit")}>Resubmit</Button>
              )}
            </Box>
          </Box>
        ))}
      </Stack>
    </Paper>
  );
}

function MedTable({
  title, rows, empty, editable, inpatient, pendingIds, canSubmitOrder, onEdit, onDiscontinue, onMistake, onGive, onClear, onSubmitOrder,
}: {
  title: string;
  rows: Medication[];
  empty: string;
  editable: boolean;
  inpatient: boolean;
  pendingIds?: Set<string>;
  canSubmitOrder?: boolean;
  onEdit?: (row: Medication) => void;
  onDiscontinue?: (row: Medication) => void;
  onMistake?: (row: Medication) => void;
  onGive?: (row: Medication) => void;
  onClear?: (row: Medication) => void;
  onSubmitOrder?: (row: Medication) => void;
}) {
  if (rows.length === 0) return empty ? <EmptyState title={empty}>Medications added to this chart show up here.</EmptyState> : null;
  return (
    <Paper sx={{ borderRadius: "16px" }}>
      <Typography component="h2" variant="h6" sx={{ p: 2, pb: 1 }}>{title}</Typography>
      <Box sx={{ overflowX: "auto" }}>
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell>Medication</TableCell>
              <TableCell>SIG</TableCell>
              <TableCell>Dose</TableCell>
              <TableCell>How taken</TableCell>
              <TableCell>Frequency</TableCell>
              <TableCell>Adherence</TableCell>
              <TableCell>Access or cost</TableCell>
              <TableCell />
            </TableRow>
          </TableHead>
          <TableBody>
            {rows.map((row) => (
              <TableRow key={row.id ?? row.name}>
                <TableCell sx={{ fontWeight: 600 }}>
                  {row.name}{row.prescribed ? " (prescribed)" : ""}
                  {row.isCompound ? <Typography variant="caption" sx={{ display: "block", fontWeight: 700 }}>Compounded</Typography> : null}
                  {row.isCompound && row.compoundReason ? (
                    <Typography variant="caption" color="text.secondary" sx={{ display: "block" }}>{row.compoundReason}</Typography>
                  ) : null}
                  {row.isCompound && row.compoundVehicle ? (
                    <Typography variant="caption" color="text.secondary" sx={{ display: "block" }}>Vehicle: {row.compoundVehicle}</Typography>
                  ) : null}
                  {row.genericName ? <Typography variant="caption" sx={{ display: "block" }}>Generic: {row.genericName}</Typography> : null}
                  {(row.flags ?? []).map((flag) => (
                    <Typography key={flag.code} variant="caption" color="warning.main" sx={{ display: "block" }}>{flag.message}</Typography>
                  ))}
                </TableCell>
                <TableCell sx={{ whiteSpace: "nowrap", fontFamily: "ui-monospace, SFMono-Regular, Menlo, monospace" }}>
                  {row.sig || medicationSig(row.dose, row.route, row.frequency)}
                </TableCell>
                <TableCell>{row.dose}</TableCell>
                <TableCell>{row.route}</TableCell>
                <TableCell>{row.frequency}</TableCell>
                <TableCell>{row.adherence}</TableCell>
                <TableCell>{row.accessCost}</TableCell>
                <TableCell align="right">
                  {editable && onEdit && <Button size="small" onClick={() => onEdit(row)}>Edit</Button>}
                  {editable && onDiscontinue && <Button size="small" onClick={() => onDiscontinue(row)}>Discontinue</Button>}
                  {editable && onMistake && <Button size="small" color="error" onClick={() => onMistake(row)}>Entered in error</Button>}
                  {canSubmitOrder && onSubmitOrder && row.id && !(pendingIds?.has(row.id)) && (
                    <Button size="small" onClick={() => onSubmitOrder(row)}>Submit for verify</Button>
                  )}
                  {canSubmitOrder && row.id && pendingIds?.has(row.id) && (
                    <Typography component="span" variant="caption" color="text.secondary">Pending verify</Typography>
                  )}
                  {inpatient && onGive && <Button size="small" onClick={() => onGive(row)}>Give now</Button>}
                  {onClear && (row.flags ?? []).length > 0 && <Button size="small" onClick={() => onClear(row)}>Clear flag</Button>}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </Box>
    </Paper>
  );
}
