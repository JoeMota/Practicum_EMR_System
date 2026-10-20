import { Accordion, AccordionDetails, AccordionSummary, Box, Typography } from "@mui/material";
import ExpandMoreRounded from "@mui/icons-material/ExpandMoreRounded";
import type { Patient } from "../../../types";

export default function ChartReference({ patient: p }: { patient: Patient }) {
  const sections = [
    {
      title: "Visit",
      body: (
        <>
          <Typography variant="body2"><b>Chief complaint:</b> {p.chiefComplaint}</Typography>
          <Typography variant="body2" sx={{ mt: 0.75 }}><b>HPI:</b> {p.hpi}</Typography>
        </>
      ),
    },
    {
      title: "Allergies", body: p.allergies.length
        ? p.allergies.map((a) => (
          <Typography key={a.substance} variant="body2">{a.substance}{a.reaction ? ` (${a.reaction.toLowerCase()})` : ""}</Typography>
        ))
        : <Typography variant="body2" color="text.secondary">No known drug allergies</Typography>,
    },
    {
      title: "Medications", body: p.medications.map((m) => (
        <Typography key={m.id} variant="body2">{m.name} {m.dose} {m.route} {m.frequency.toLowerCase()}</Typography>
      )),
    },
    {
      title: "Labs", body: p.labs.map((l) => (
        <Row key={l.id} label={l.name} value={`${l.value} ${l.unit}${l.flag ? ` ${l.flag}` : ""}`} flag={Boolean(l.flag)} />
      )),
    },
    { title: "Vitals", body: p.vitals.map((v) => <Row key={v.label} label={v.label} value={v.value} />) },
    {
      title: "History", body: (
        <>
          <Typography variant="body2"><b>Family:</b> {p.familyHistory}</Typography>
          <Typography variant="body2"><b>Surgical:</b> {p.surgicalHistory}</Typography>
          <Typography variant="body2"><b>Social:</b> {p.socialHistory}</Typography>
        </>
      ),
    },
  ];

  return (
    <Box>
      {sections.map((s, i) => (
        <Accordion key={s.title} defaultExpanded={i < 2} disableGutters elevation={0} sx={{ border: "none", "&:before": { display: "none" } }}>
          <AccordionSummary expandIcon={<ExpandMoreRounded />}>
            <Typography variant="subtitle2">{s.title}</Typography>
          </AccordionSummary>
          <AccordionDetails sx={{ pt: 0 }}>
            {Array.isArray(s.body) && s.body.length === 0 ? (
              <Typography variant="body2" color="text.secondary">None recorded</Typography>
            ) : s.body}
          </AccordionDetails>
        </Accordion>
      ))}
    </Box>
  );
}

function Row({ label, value, flag }: { label: string; value: string; flag?: boolean }) {
  return (
    <Box sx={{ display: "flex", justifyContent: "space-between", gap: 2 }}>
      <Typography variant="body2">{label}</Typography>
      <Typography variant="body2" sx={{ fontWeight: flag ? 700 : 400, color: flag ? "error.main" : "text.primary", whiteSpace: "nowrap" }}>
        {value}
      </Typography>
    </Box>
  );
}
