import { useEffect, useState } from "react";
import { Box, Button, Chip, Paper, Typography } from "@mui/material";
import WarningAmberRounded from "@mui/icons-material/WarningAmberRounded";
import type { Patient } from "../../../types";
import { getPatientPhoto } from "../../../api/patients";
import { listOpened } from "../../../api/chart";
import { useAsync } from "../../../utils/useAsync";
import { formatDate } from "../../../utils/format";
import { utep } from "../../../theme/tokens";
import { useSession } from "../../auth/useSession";
import { phaseChip } from "../simulation";

interface Props {
  patient: Patient;
  ownerName?: string;
  onEditStatus?: () => void;
  compact?: boolean;
}

const card = { borderRadius: 1, overflow: "hidden", border: "none", boxShadow: `inset 0 0 0 1px ${utep.lineSoft}` } as const;

export default function PatientBanner({ patient: p, ownerName, onEditStatus, compact }: Props) {
  const { activeRole } = useSession();
  const opened = useAsync(
    () => (p.mode === "simulation" ? listOpened(activeRole, p.id) : Promise.resolve([])),
    [activeRole, p.id, p.mode],
  );
  const initials = `${p.firstName[0] ?? ""}${p.lastName[0] ?? ""}`;
  const [photo, setPhoto] = useState<{ id: string; src: string }>();
  useEffect(() => {
    if (!p.hasPhoto) return;
    let live = true;
    getPatientPhoto(activeRole, p.id)
      .then((row) => { if (live) setPhoto({ id: p.id, src: `data:${row.contentType};base64,${row.data}` }); })
      .catch(() => undefined);
    return () => { live = false; };
  }, [activeRole, p.hasPhoto, p.id]);
  const shownPhoto = p.hasPhoto && photo?.id === p.id ? photo.src : undefined;
  const phase = phaseChip(p.simulationPhase);
  const openedLine = (opened.data ?? []).length
    ? `Opened by ${opened.data!.map((person) => person.station ? `${person.name} (${person.station})` : person.name).join(", ")}`
    : "";
  const statusLabel = p.mode === "case"
    ? "Case master"
    : p.mode === "assessment"
      ? (ownerName ? `Assessment · ${ownerName}` : "Assessment · your copy")
      : p.mode === "simulation"
        ? phase.label
        : `${p.practiceLabel ?? "Practice"} · not graded`;
  const statusChip = p.mode === "simulation"
    ? { bgcolor: phase.bgcolor, color: phase.color }
    : p.mode === "practice"
      ? { bgcolor: "transparent", color: utep.navy, border: `1px solid ${utep.line}` }
      : { bgcolor: utep.navy, color: "#fff" };
  const emergency = [p.emergencyContact?.name, p.emergencyContact?.relationship && `(${p.emergencyContact.relationship})`]
    .filter(Boolean)
    .join(" ");
  const emergencyLine = [emergency, p.emergencyContact?.phone].filter(Boolean).join(" · ");
  const codeAlert = p.codeStatus === "DNR" || p.codeStatus === "DNI";
  const statusItems: [string, string][] = [
    ["Visit", p.status.encounter],
    ["Setting", p.status.careSetting],
    ["Record", p.status.lifecycle],
    ...(p.status.program ? ([["Program", p.status.program]] as [string, string][]) : []),
    ...(p.codeStatus ? ([["Code status", p.codeStatus]] as [string, string][]) : []),
    ...(emergencyLine ? ([["Emergency", emergencyLine]] as [string, string][]) : []),
  ];

  return (
    <Paper component="section" aria-label="Patient" sx={card}>
      <Box
        sx={{
          p: compact ? 2 : 2.5,
          display: "grid",
          gap: 2,
          gridTemplateColumns: "auto minmax(0, 1fr)",
          alignItems: "start",
        }}
      >
        <Box
          aria-hidden={shownPhoto ? undefined : true}
          sx={{
            width: compact ? 44 : 52, height: compact ? 44 : 52, borderRadius: "50%",
            bgcolor: utep.navy, color: "#fff", display: "grid", placeItems: "center",
            fontWeight: 800, fontSize: compact ? 16 : 18, overflow: "hidden",
          }}
        >
          {shownPhoto ? (
            <Box component="img" src={shownPhoto} alt={`${p.firstName} ${p.lastName}`} sx={{ width: "100%", height: "100%", objectFit: "cover" }} />
          ) : initials}
        </Box>

        <Box sx={{ minWidth: 0 }}>
          {!compact && (
            <Typography variant="overline" sx={{ color: utep.ink2, fontWeight: 700, letterSpacing: 0 }}>
              Patient profile
            </Typography>
          )}
          <Typography component={compact ? "p" : "h1"} variant={compact ? "h6" : "h5"} sx={{ color: utep.navy, lineHeight: 1.2 }}>
            {p.lastName}, {p.firstName}
            {p.preferredName && (
              <Typography component="span" variant="body1" color="text.secondary"> ({p.preferredName})</Typography>
            )}
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
            {p.ageYears} y, {p.sexAtBirth}{p.pronouns ? ` (${p.pronouns})` : ""}, DOB {formatDate(p.dob)}, MRN {p.mrn}
          </Typography>
          <Box sx={{ display: "flex", gap: 1, mt: 1, flexWrap: "wrap", alignItems: "center" }}>
            <Chip size="small" label={statusLabel} sx={statusChip} />
            {p.codeStatus && (
              <Chip
                size="small"
                label={p.codeStatus}
                sx={codeAlert
                  ? { bgcolor: utep.alertSoft, color: utep.alert, fontWeight: 700 }
                  : { bgcolor: "action.hover", color: utep.ink2 }}
              />
            )}
            {p.hipaaOnFile && (
              <Chip size="small" label="HIPAA on file" sx={{ bgcolor: "action.hover", color: utep.ink2 }} />
            )}
            <Typography variant="caption" color="text.secondary">
              {[
                p.mode === "simulation" && p.viewerStation ? `You are the ${p.viewerStation}` : "",
                openedLine,
                "Simulated patient",
              ].filter(Boolean).join(" · ")}
            </Typography>
          </Box>
        </Box>

        {!compact && (
          <Box
            component="dl"
            sx={{ m: 0, display: "flex", flexWrap: "wrap", columnGap: 3.5, rowGap: 1, alignItems: "flex-end", gridColumn: "1 / -1" }}
          >
            {statusItems.map(([k, v]) => (
              <Box key={k}>
                <Typography component="dt" variant="caption" color="text.secondary">{k}</Typography>
                <Typography component="dd" variant="body2" sx={{ m: 0, fontWeight: 700 }}>{v}</Typography>
              </Box>
            ))}
            {onEditStatus && (
              <Button size="small" variant="outlined" onClick={onEditStatus}>Change status</Button>
            )}
          </Box>
        )}
      </Box>

      <Box
        role="note"
        aria-label="Allergies"
        sx={{
          px: compact ? 2 : 2.5, py: 1, display: "flex", alignItems: "center", gap: 1,
          bgcolor: p.allergies.length ? utep.alertSoft : "action.hover",
          borderTop: 1, borderColor: p.allergies.length ? "#F4C7C3" : "divider",
          color: p.allergies.length ? utep.alert : "text.secondary",
        }}
      >
        {p.allergies.length > 0 && <WarningAmberRounded fontSize="small" />}
        <Typography variant="body2" sx={{ fontWeight: 700 }}>
          {p.allergies.length
            ? `Allergies: ${p.allergies.map((a) => `${a.substance}${a.reaction ? ` (${a.reaction.toLowerCase()})` : ""}`).join("; ")}`
            : "No known drug allergies"}
        </Typography>
      </Box>
    </Paper>
  );
}
