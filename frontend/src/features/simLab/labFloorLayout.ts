/** Floor geometry traced from the UTEP Sim Center plan (assignable rooms only).
 * Coordinates are in a 640×360 viewBox. Storage / out-of-scope areas are decorative.
 */

export type FloorRoomShape = {
  number: string;
  x: number;
  y: number;
  w: number;
  h: number;
  beds?: number;
  bedRows?: number;
};

/** Assignable teaching rooms — clickable when present in the API catalog. */
export const FLOOR_ROOMS: FloorRoomShape[] = [
  // Top-left big lab (10 beds)
  { number: "126", x: 24, y: 28, w: 168, h: 118, beds: 10, bedRows: 2 },
  // Top mid ward
  { number: "127", x: 200, y: 28, w: 92, h: 78, beds: 5, bedRows: 1 },
  // Exam stack (doctor visit)
  { number: "112", x: 220, y: 118, w: 52, h: 36 },
  { number: "113", x: 220, y: 158, w: 52, h: 36 },
  { number: "115", x: 220, y: 198, w: 52, h: 36 },
  { number: "116", x: 220, y: 238, w: 52, h: 36 },
  // Testing row
  { number: "110", x: 290, y: 168, w: 58, h: 42 },
  { number: "108", x: 352, y: 168, w: 58, h: 42 },
  { number: "107", x: 414, y: 168, w: 58, h: 42 },
  { number: "106", x: 476, y: 168, w: 58, h: 42 },
  // Bottom ward row (5 beds each)
  { number: "120", x: 24, y: 288, w: 88, h: 56, beds: 5, bedRows: 1 },
  { number: "111", x: 116, y: 288, w: 88, h: 56, beds: 5, bedRows: 1 },
  { number: "109", x: 208, y: 288, w: 88, h: 56, beds: 5, bedRows: 1 },
  { number: "105", x: 300, y: 288, w: 88, h: 56, beds: 5, bedRows: 1 },
  { number: "104", x: 392, y: 288, w: 88, h: 56, beds: 5, bedRows: 1 },
  // Right lab
  { number: "103", x: 500, y: 248, w: 116, h: 96, beds: 5, bedRows: 1 },
];

/** Grayed storage / non-teaching zones from the red-marked areas on the paper plan. */
export const FLOOR_STORAGE: { x: number; y: number; w: number; h: number; label?: string }[] = [
  { x: 24, y: 156, w: 72, h: 118, label: "Storage" },
  { x: 100, y: 156, w: 100, h: 118, label: "Storage" },
  { x: 300, y: 28, w: 120, h: 120, label: "Staff" },
  { x: 440, y: 28, w: 176, h: 120, label: "Storage" },
  { x: 548, y: 168, w: 68, h: 64 },
];

export const FLOOR_VIEW = { w: 640, h: 360 };

export function bedMarkers(room: FloorRoomShape): { x: number; y: number; w: number; h: number }[] {
  const count = room.beds ?? 0;
  if (!count) return [];
  const rows = room.bedRows ?? 1;
  const cols = Math.ceil(count / rows);
  const pad = 8;
  const gap = 4;
  const usableW = room.w - pad * 2;
  const usableH = room.h - pad * 2 - 14;
  const bedW = Math.min(14, (usableW - gap * (cols - 1)) / cols);
  const bedH = Math.min(10, (usableH - gap * (rows - 1)) / rows);
  const marks: { x: number; y: number; w: number; h: number }[] = [];
  for (let i = 0; i < count; i += 1) {
    const row = Math.floor(i / cols);
    const col = i % cols;
    marks.push({
      x: room.x + pad + col * (bedW + gap),
      y: room.y + pad + 12 + row * (bedH + gap),
      w: bedW,
      h: bedH,
    });
  }
  return marks;
}
