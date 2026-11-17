import { Box, Typography } from "@mui/material";
import { utep } from "../../theme/tokens";
import type { SimLabRoom } from "../../api/simLab";
import {
  FLOOR_ROOMS, FLOOR_STORAGE, FLOOR_VIEW, bedMarkers, type FloorRoomShape,
} from "./labFloorLayout";

interface Props {
  rooms: SimLabRoom[];
  highlightNumber?: string | null;
  compact?: boolean;
  onSelectRoom?: (room: SimLabRoom) => void;
  selectedId?: string | null;
}

function kindTint(kind: string | undefined, active: boolean): string {
  if (active) return utep.orangeSoft;
  if (kind === "testing") return "#EEF4FA";
  if (kind === "exam") return "#F7F3EC";
  if (kind === "big_lab") return "#F3F6FB";
  return utep.paper;
}

export default function LabFloorMap({
  rooms, highlightNumber, compact, onSelectRoom, selectedId,
}: Props) {
  const byNumber = new Map(rooms.map((r) => [r.number, r]));
  const selected = rooms.find((r) => r.id === selectedId);
  const activeNumber = highlightNumber || selected?.number || null;

  function handleClick(shape: FloorRoomShape) {
    const apiRoom = byNumber.get(shape.number);
    if (apiRoom && onSelectRoom) onSelectRoom(apiRoom);
  }

  return (
    <Box
      role="img"
      aria-label={
        activeNumber
          ? `Sim Center floor plan. Highlighted room ${activeNumber}.`
          : "Sim Center floor plan"
      }
      sx={{
        width: "100%",
        maxWidth: compact ? 320 : 720,
        border: `1px solid ${utep.line}`,
        borderRadius: 2,
        bgcolor: "#FBFCFD",
        overflow: "hidden",
        boxShadow: compact ? "none" : "0 1px 2px rgba(14,34,80,0.06)",
      }}
    >
      <Box
        sx={{
          px: 1.5,
          py: 0.85,
          borderBottom: `1px solid ${utep.line}`,
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          gap: 1,
          flexWrap: "wrap",
        }}
      >
        <Typography sx={{ fontSize: 13, fontWeight: 700, color: utep.navy }}>
          UTEP Sim Center
        </Typography>
        <Box sx={{ display: "flex", gap: 1.25, flexWrap: "wrap" }}>
          {[
            { label: "Lab", color: utep.paper },
            { label: "Testing", color: "#EEF4FA" },
            { label: "Exam", color: "#F7F3EC" },
            { label: "Storage", color: "#E6E9EE" },
          ].map((item) => (
            <Box key={item.label} sx={{ display: "flex", alignItems: "center", gap: 0.5 }}>
              <Box sx={{ width: 10, height: 10, borderRadius: 0.5, bgcolor: item.color, border: `1px solid ${utep.line}` }} />
              <Typography sx={{ fontSize: 11, color: utep.ink2 }}>{item.label}</Typography>
            </Box>
          ))}
        </Box>
      </Box>

      <Box sx={{ p: compact ? 0.75 : 1.25, bgcolor: "#F0F3F7" }}>
        <svg
          viewBox={`0 0 ${FLOOR_VIEW.w} ${FLOOR_VIEW.h}`}
          width="100%"
          style={{ display: "block", height: "auto" }}
        >
          {/* Building shell */}
          <rect x="12" y="16" width="616" height="328" rx="6" fill="#E8EDF3" stroke={utep.navy} strokeWidth="2.2" />
          {/* Main corridors */}
          <rect x="180" y="150" width="360" height="28" fill="#D9E0EA" />
          <rect x="180" y="150" width="28" height="130" fill="#D9E0EA" />
          <text x="320" y="168" textAnchor="middle" fontSize="11" fill="#7A8699" fontWeight="600">
            Corridor
          </text>

          {FLOOR_STORAGE.map((zone, idx) => (
            <g key={`storage-${idx}`}>
              <rect
                x={zone.x}
                y={zone.y}
                width={zone.w}
                height={zone.h}
                fill="#E6E9EE"
                stroke="#C5CCD6"
                strokeWidth="1"
                strokeDasharray="4 3"
                rx="3"
              />
              {zone.label && (
                <text
                  x={zone.x + zone.w / 2}
                  y={zone.y + zone.h / 2 + 4}
                  textAnchor="middle"
                  fontSize="11"
                  fill="#9AA3B2"
                  fontWeight="600"
                >
                  {zone.label}
                </text>
              )}
            </g>
          ))}

          {FLOOR_ROOMS.map((shape) => {
            const api = byNumber.get(shape.number);
            const active = activeNumber === shape.number;
            const clickable = Boolean(api && onSelectRoom);
            const fill = kindTint(api?.kind, active);
            const stroke = active ? utep.orange : utep.navy;
            const strokeW = active ? 3 : 1.4;
            return (
              <g
                key={shape.number}
                onClick={() => handleClick(shape)}
                style={{ cursor: clickable ? "pointer" : "default" }}
              >
                <rect
                  x={shape.x}
                  y={shape.y}
                  width={shape.w}
                  height={shape.h}
                  fill={fill}
                  stroke={stroke}
                  strokeWidth={strokeW}
                  rx="4"
                />
                <text
                  x={shape.x + 8}
                  y={shape.y + 16}
                  fontSize={compact ? 12 : 13}
                  fontWeight="700"
                  fill={utep.navy}
                >
                  {shape.number}
                </text>
                {bedMarkers(shape).map((bed, i) => (
                  <rect
                    key={`${shape.number}-bed-${i}`}
                    x={bed.x}
                    y={bed.y}
                    width={bed.w}
                    height={bed.h}
                    rx="1.5"
                    fill={active ? "#F3C39A" : "#D7DEE8"}
                    stroke={active ? utep.orange : "#B7C0CE"}
                    strokeWidth="0.8"
                  />
                ))}
                {active && (
                  <text
                    x={shape.x + shape.w / 2}
                    y={shape.y + shape.h - 6}
                    textAnchor="middle"
                    fontSize="10"
                    fontWeight="700"
                    fill={utep.orange}
                  >
                    {highlightNumber === shape.number ? "You are here" : "Selected"}
                  </text>
                )}
              </g>
            );
          })}
        </svg>
      </Box>

      {activeNumber && (
        <Typography sx={{ px: 1.5, py: 0.85, fontSize: 12, color: utep.ink2, borderTop: `1px solid ${utep.line}` }}>
          Highlighted: Room {activeNumber}
          {byNumber.get(activeNumber)?.bedCount && byNumber.get(activeNumber)!.bedCount > 1
            ? ` · ${byNumber.get(activeNumber)!.bedCount} beds`
            : ""}
        </Typography>
      )}
    </Box>
  );
}
