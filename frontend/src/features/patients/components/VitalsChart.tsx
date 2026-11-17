import { useMemo, useState } from "react";
import { Box, IconButton, Typography } from "@mui/material";
import AddRounded from "@mui/icons-material/AddRounded";
import RemoveRounded from "@mui/icons-material/RemoveRounded";
import type { Patient, Vital } from "../../../types";
import { utep } from "../../../theme/tokens";

type Range = "year" | "month" | "week" | "day" | "hour";

const RANGES: { id: Range; label: string; windowMs: number }[] = [
  { id: "year", label: "Year", windowMs: 365 * 24 * 60 * 60 * 1000 },
  { id: "month", label: "Month", windowMs: 31 * 24 * 60 * 60 * 1000 },
  { id: "week", label: "Week", windowMs: 7 * 24 * 60 * 60 * 1000 },
  { id: "day", label: "Day", windowMs: 24 * 60 * 60 * 1000 },
  { id: "hour", label: "Hour", windowMs: 60 * 60 * 1000 },
];

interface Point {
  at: number | null;
  value: number;
  caption: string;
}

interface Series {
  id: string;
  label: string;
  unit: string;
  valueLabel: string;
  high?: boolean;
  points: Point[];
}

function firstNumber(s: string) {
  const match = s.match(/-?\d+(?:\.\d+)?/);
  return match ? Number(match[0]) : undefined;
}

function when(vital: Vital): number | null {
  if (!vital.recordedAt) return null;
  const time = new Date(vital.recordedAt).getTime();
  return Number.isNaN(time) ? null : time;
}

function caption(at: number | null) {
  if (at == null) return "On file";
  return new Date(at).toLocaleString("en-US", { month: "short", day: "numeric", hour: "numeric", minute: "2-digit" });
}

function readings(vitals: Vital[], include: (vital: Vital) => boolean, valueOf: (vital: Vital) => number | undefined): Point[] {
  return vitals
    .filter((vital) => vital.status !== "entered_in_error" && include(vital))
    .map((vital) => {
      const value = valueOf(vital);
      const at = when(vital);
      return value == null ? null : { at, value, caption: caption(at) };
    })
    .filter((point): point is Point => point != null)
    .sort((a, b) => (a.at ?? 0) - (b.at ?? 0));
}

function seriesFrom(patient: Patient): Series[] {
  const vitals = patient.vitals;
  const series: Series[] = [];
  const pulse = readings(vitals, (vital) => /pulse|heart/i.test(vital.label), (vital) => firstNumber(vital.value));
  if (pulse.length) {
    const current = pulse[pulse.length - 1].value;
    series.push({
      id: "hr", label: "Heart rate", unit: "bpm", valueLabel: String(Math.round(current)),
      high: current > 100, points: pulse,
    });
  }
  const bp = readings(vitals, (vital) => /^bp$/i.test(vital.label) || /blood pressure/i.test(vital.label), (vital) => {
    const match = vital.value.match(/(\d+)\s*\/\s*(\d+)/);
    return match ? Number(match[1]) : undefined;
  });
  const dia = readings(vitals, (vital) => /^bp$/i.test(vital.label) || /blood pressure/i.test(vital.label), (vital) => {
    const match = vital.value.match(/(\d+)\s*\/\s*(\d+)/);
    return match ? Number(match[2]) : undefined;
  });
  if (bp.length) {
    series.push({
      id: "sys", label: "BP systolic", unit: "mmHg", valueLabel: String(bp[bp.length - 1].value),
      high: bp[bp.length - 1].value >= 140, points: bp,
    });
  }
  if (dia.length) {
    series.push({
      id: "dia", label: "BP diastolic", unit: "mmHg", valueLabel: String(dia[dia.length - 1].value),
      high: dia[dia.length - 1].value >= 90, points: dia,
    });
  }
  const seen = new Set<string>();
  for (const vital of vitals) {
    if (vital.status === "entered_in_error" || /pulse|heart|^bp$|blood pressure/i.test(vital.label)) continue;
    const id = vital.label.toLowerCase();
    if (seen.has(id)) continue;
    seen.add(id);
    const points = readings(vitals, (item) => item.label.toLowerCase() === id, (item) => firstNumber(item.value));
    if (!points.length) continue;
    const current = points[points.length - 1].value;
    const high = /pain/i.test(vital.label) ? current >= 7
      : /temp/i.test(vital.label) ? current >= 100.4
      : /rr|respir/i.test(vital.label) ? current > 20
      : /spo/i.test(vital.label) ? current < 92
      : undefined;
    series.push({ id, label: vital.label, unit: "", valueLabel: String(current), high, points });
  }
  return series;
}

function inWindow(points: Point[], windowMs: number): Point[] {
  const newest = Math.max(...points.map((point) => point.at ?? 0));
  if (!newest) return points;
  const filtered = points.filter((point) => point.at == null || newest - point.at <= windowMs);
  return filtered.length ? filtered : points;
}

export default function VitalsChart({ patient }: { patient: Patient }) {
  const series = useMemo(() => seriesFrom(patient), [patient]);
  const [selected, setSelected] = useState(series[0]?.id ?? "");
  const [range, setRange] = useState<Range>("year");
  const active = series.find((item) => item.id === selected) ?? series[0];
  const rangeIdx = RANGES.findIndex((item) => item.id === range);
  const shown = useMemo(() => {
    if (!active) return [];
    const spec = RANGES.find((item) => item.id === range)!;
    return inWindow(active.points, spec.windowMs);
  }, [active, range]);

  if (!active) {
    return <Typography variant="body2" color="text.secondary">No numeric vitals to trend yet.</Typography>;
  }

  const shiftRange = (dir: 1 | -1) => {
    const next = Math.min(RANGES.length - 1, Math.max(0, rangeIdx + dir));
    setRange(RANGES[next].id);
  };

  return (
    <Box>
      <Box role="tablist" aria-label="Vital signs" sx={{ display: "flex", gap: 0.75, flexWrap: "nowrap", overflowX: "auto", mb: 2, pb: 0.5 }}>
        {series.map((item) => {
          const on = item.id === active.id;
          return (
            <Box
              key={item.id} component="button" type="button" role="tab" aria-selected={on}
              onClick={() => setSelected(item.id)}
              sx={{
                appearance: "none", border: on ? "none" : `1px solid ${utep.line}`,
                cursor: "pointer", textAlign: "left", px: 1.5, py: 1, minWidth: 108, flexShrink: 0,
                borderRadius: "12px", bgcolor: on ? utep.navy : "#F7F8FB", color: on ? "#fff" : utep.ink,
                "&:focus-visible": { outline: `3px solid ${utep.orange}`, outlineOffset: 2 },
              }}
            >
              <Typography sx={{ fontSize: 12, fontWeight: 600, opacity: 0.85, lineHeight: 1.2 }}>{item.label}</Typography>
              <Typography sx={{ fontSize: 16, fontWeight: 800, lineHeight: 1.3, color: on ? utep.orange : item.high ? utep.alert : utep.navy }}>
                {item.high ? "▲ " : "● "}{item.valueLabel}
                {item.unit && <Box component="span" sx={{ fontSize: 12, fontWeight: 600, ml: 0.5, opacity: 0.8 }}>{item.unit}</Box>}
              </Typography>
            </Box>
          );
        })}
      </Box>

      <TrendSvg points={shown.map((point) => point.value)} labels={shown.map((point) => point.caption)} />

      <Box sx={{ display: "flex", alignItems: "center", gap: 1, mt: 1.25, flexWrap: "wrap" }}>
        <IconButton aria-label="Narrower time range" size="small" onClick={() => shiftRange(1)} disabled={rangeIdx === RANGES.length - 1}>
          <AddRounded fontSize="small" />
        </IconButton>
        <IconButton aria-label="Wider time range" size="small" onClick={() => shiftRange(-1)} disabled={rangeIdx === 0}>
          <RemoveRounded fontSize="small" />
        </IconButton>
        {RANGES.map((item) => {
          const on = item.id === range;
          return (
            <Box
              key={item.id} component="button" type="button" onClick={() => setRange(item.id)}
              sx={{
                appearance: "none", border: "none", background: "none", cursor: "pointer",
                px: 1, py: 0.5, fontWeight: on ? 800 : 600, fontSize: 13,
                color: on ? utep.navy : utep.ink2,
                borderBottom: on ? `2px solid ${utep.orange}` : "2px solid transparent",
                "&:focus-visible": { outline: `3px solid ${utep.navy}`, outlineOffset: 2 },
              }}
            >
              {item.label}
            </Box>
          );
        })}
      </Box>
    </Box>
  );
}

function TrendSvg({ points, labels }: { points: number[]; labels: string[] }) {
  if (points.length === 0) return null;
  const w = 720;
  const h = 220;
  const pad = { l: 40, r: 8, t: 12, b: 28 };
  const min = Math.min(...points);
  const max = Math.max(...points);
  const span = max - min || 1;
  const niceMin = min - span * 0.15;
  const niceMax = max + span * 0.15;
  const niceSpan = niceMax - niceMin;
  const x = (i: number) => pad.l + (i / Math.max(points.length - 1, 1)) * (w - pad.l - pad.r);
  const y = (v: number) => pad.t + (1 - (v - niceMin) / niceSpan) * (h - pad.t - pad.b);
  const line = points.map((v, i) => `${i === 0 ? "M" : "L"}${x(i).toFixed(1)},${y(v).toFixed(1)}`).join(" ");
  const area = `${line} L${x(points.length - 1).toFixed(1)},${h - pad.b} L${pad.l},${h - pad.b} Z`;
  const ticks = 5;
  const yTicks = Array.from({ length: ticks }, (_, i) => niceMin + (niceSpan * i) / (ticks - 1));
  const labelEvery = Math.ceil(labels.length / 6);

  return (
    <Box sx={{ width: "100%", overflow: "hidden" }}>
      <svg viewBox={`0 0 ${w} ${h}`} role="img" aria-label="Vital sign trend from recorded values" style={{ width: "100%", height: "auto", display: "block" }}>
        {yTicks.map((tick) => (
          <g key={tick}>
            <line x1={pad.l} x2={w - pad.r} y1={y(tick)} y2={y(tick)} stroke={utep.line} strokeDasharray="4 6" />
            <text x={pad.l - 8} y={y(tick) + 4} textAnchor="end" fill={utep.ink2} fontSize="11" fontFamily="Source Sans 3, sans-serif">
              {Math.round(tick)}
            </text>
          </g>
        ))}
        <path d={area} fill={utep.orange} fillOpacity="0.12" />
        <path d={line} fill="none" stroke={utep.navy} strokeWidth="2.5" strokeLinejoin="round" strokeLinecap="round" />
        {points.map((value, i) => (
          <circle key={i} cx={x(i)} cy={y(value)} r={i === points.length - 1 ? 5 : 3.5} fill={i === points.length - 1 ? utep.orange : utep.navy} stroke="#fff" strokeWidth="1.5" />
        ))}
        {labels.map((label, i) =>
          i % labelEvery === 0 ? (
            <text key={`${label}-${i}`} x={x(i)} y={h - 8} textAnchor="middle" fill={utep.ink2} fontSize="11" fontFamily="Source Sans 3, sans-serif">
              {label}
            </text>
          ) : null,
        )}
      </svg>
    </Box>
  );
}
