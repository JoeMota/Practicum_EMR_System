import { useMemo, useState } from "react";
import {
  Alert, Box, Button, FormControl, InputLabel, LinearProgress, MenuItem, Select,
  Table, TableBody, TableCell, TableHead, TableRow, TextField, Typography,
} from "@mui/material";
import { useSession } from "../auth/useSession";
import { useAsync } from "../../utils/useAsync";
import { usePageHeading } from "../../components/usePageHeading";
import PageError from "../../components/PageError";
import { listRoster } from "../../api/roster";
import {
  assignSimLab, assignmentSummary, clearSimLabAssignment,
  listSimLabAssignments, listSimLabRooms, type SimLabRoom,
} from "../../api/simLab";
import { utep } from "../../theme/tokens";
import LabFloorMap from "./LabFloorMap";

function todayISO() {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
}

const ROLE_OPTIONS = ["", "Patient", "Nurse", "Provider"];
const BLOCK_OPTIONS = ["", "8:00–9:00", "9:00–10:00", "10:00–11:00", "11:00–12:00", "13:00–14:00", "14:00–15:00"];

export default function LabCheckinPage() {
  usePageHeading("Lab check-in");
  const { activeRole, courseId } = useSession();
  const [sessionDate, setSessionDate] = useState(todayISO);
  const [userId, setUserId] = useState("");
  const [roomId, setRoomId] = useState("");
  const [bed, setBed] = useState("");
  const [roleLabel, setRoleLabel] = useState("");
  const [timeBlock, setTimeBlock] = useState("");
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [tick, setTick] = useState(0);

  const rooms = useAsync(
    () => (courseId ? listSimLabRooms(courseId, activeRole) : Promise.resolve([])),
    [courseId, activeRole],
  );
  const roster = useAsync(
    () => (courseId ? listRoster(courseId) : Promise.resolve([])),
    [courseId],
  );
  const board = useAsync(
    () => (courseId
      ? listSimLabAssignments(courseId, activeRole, sessionDate)
      : Promise.resolve([])),
    [courseId, activeRole, sessionDate, tick],
  );

  const selectedRoom: SimLabRoom | undefined = useMemo(
    () => rooms.data?.find((r) => r.id === roomId),
    [rooms.data, roomId],
  );
  const students = useMemo(() => {
    const assigned = new Set((board.data ?? []).map((a) => a.userId));
    return (roster.data ?? [])
      .filter((u) => u.rosterStatus !== "inactive")
      .sort((a, b) => a.fullName.localeCompare(b.fullName))
      .map((u) => ({ ...u, assigned: assigned.has(u.id) }));
  }, [roster.data, board.data]);

  if (!courseId) return <Alert severity="info">Select a course first.</Alert>;
  if (rooms.error) return <PageError error={rooms.error} />;
  if (!rooms.data) return <LinearProgress aria-label="Loading rooms" />;

  async function save() {
    setError("");
    setMessage("");
    if (!userId || !roomId) {
      setError("Pick a student and a room.");
      return;
    }
    setBusy(true);
    try {
      const row = await assignSimLab(courseId, activeRole, {
        userId,
        roomId,
        sessionDate,
        bed: bed || undefined,
        roleLabel: roleLabel || undefined,
        timeBlock: selectedRoom?.timing === "hour" ? (timeBlock || undefined) : undefined,
      });
      setMessage(`Checked in ${row.studentName} — ${assignmentSummary(row)}`);
      setTick((n) => n + 1);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not save assignment.");
    } finally {
      setBusy(false);
    }
  }

  async function clearRow(id: string) {
    setBusy(true);
    setError("");
    try {
      await clearSimLabAssignment(courseId, activeRole, id);
      setMessage("Cleared assignment.");
      setTick((n) => n + 1);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not clear.");
    } finally {
      setBusy(false);
    }
  }

  const kindLabel = (kind: string) => {
    if (kind === "big_lab") return "Big lab";
    if (kind === "ward") return "Lab";
    if (kind === "testing") return "Testing";
    return "Exam";
  };

  return (
    <Box sx={{ display: "grid", gap: 2.5, maxWidth: 1180 }}>
      <Typography sx={{ color: utep.ink2, maxWidth: 720 }}>
        Assign students to Sim Center rooms. Click a room on the map or use the dropdown.
        Bed, role, and time block are optional. Big labs are for the day; testing and exam rooms can use hour blocks.
      </Typography>

      {error && <Alert severity="error">{error}</Alert>}
      {message && <Alert severity="success" onClose={() => setMessage("")}>{message}</Alert>}

      <LabFloorMap
        rooms={rooms.data ?? []}
        selectedId={roomId || null}
        onSelectRoom={(r) => {
          setRoomId(r.id);
          setBed("");
          setTimeBlock("");
        }}
      />

      <Box sx={{ display: "grid", gap: 2, gridTemplateColumns: { xs: "1fr", md: "1fr 1fr" } }}>
        <Box sx={{ display: "grid", gap: 1.5, p: 2, border: `1px solid ${utep.line}`, borderRadius: 2, bgcolor: utep.paper }}>
          <TextField
            label="Lab date"
            type="date"
            size="small"
            value={sessionDate}
            onChange={(e) => setSessionDate(e.target.value)}
            slotProps={{ inputLabel: { shrink: true } }}
          />
          <FormControl size="small" fullWidth>
            <InputLabel id="student-label">Student</InputLabel>
            <Select
              labelId="student-label"
              label="Student"
              value={userId}
              onChange={(e) => setUserId(e.target.value)}
            >
              {students.map((s) => (
                <MenuItem key={s.id} value={s.id}>
                  {s.fullName}{s.assigned ? " (assigned)" : ""}
                </MenuItem>
              ))}
            </Select>
          </FormControl>
          <FormControl size="small" fullWidth>
            <InputLabel id="room-label">Room</InputLabel>
            <Select
              labelId="room-label"
              label="Room"
              value={roomId}
              onChange={(e) => {
                setRoomId(e.target.value);
                setBed("");
                setTimeBlock("");
              }}
            >
              {(rooms.data ?? []).map((r) => (
                <MenuItem key={r.id} value={r.id}>
                  {r.number} · {kindLabel(r.kind)}
                  {r.bedCount > 1 ? ` · ${r.bedCount} beds` : ""}
                </MenuItem>
              ))}
            </Select>
          </FormControl>
          {selectedRoom && selectedRoom.bedCount > 1 && (
            <FormControl size="small" fullWidth>
              <InputLabel id="bed-label">Bed (optional)</InputLabel>
              <Select
                labelId="bed-label"
                label="Bed (optional)"
                value={bed}
                onChange={(e) => setBed(e.target.value)}
              >
                <MenuItem value="">None</MenuItem>
                {selectedRoom.bedOptions.map((b) => (
                  <MenuItem key={b} value={b}>Bed {b}</MenuItem>
                ))}
              </Select>
            </FormControl>
          )}
          <FormControl size="small" fullWidth>
            <InputLabel id="role-label">Role (optional)</InputLabel>
            <Select
              labelId="role-label"
              label="Role (optional)"
              value={roleLabel}
              onChange={(e) => setRoleLabel(e.target.value)}
            >
              {ROLE_OPTIONS.map((r) => (
                <MenuItem key={r || "none"} value={r}>{r || "None"}</MenuItem>
              ))}
            </Select>
          </FormControl>
          {selectedRoom?.timing === "hour" && (
            <FormControl size="small" fullWidth>
              <InputLabel id="block-label">Time block (optional)</InputLabel>
              <Select
                labelId="block-label"
                label="Time block (optional)"
                value={timeBlock}
                onChange={(e) => setTimeBlock(e.target.value)}
              >
                {BLOCK_OPTIONS.map((b) => (
                  <MenuItem key={b || "none"} value={b}>{b || "None"}</MenuItem>
                ))}
              </Select>
            </FormControl>
          )}
          <Button variant="contained" disabled={busy} onClick={save} sx={{ justifySelf: "start" }}>
            Check in
          </Button>
        </Box>

        <Box sx={{ border: `1px solid ${utep.line}`, borderRadius: 2, overflow: "hidden", bgcolor: utep.paper }}>
          <Typography sx={{ px: 2, py: 1.25, fontWeight: 700, borderBottom: `1px solid ${utep.line}` }}>
            Checked in · {sessionDate}
          </Typography>
          {board.loading && !board.data ? (
            <LinearProgress />
          ) : (board.data?.length ?? 0) === 0 ? (
            <Typography sx={{ p: 2, color: utep.ink2 }}>No students checked in for this date yet.</Typography>
          ) : (
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell>Student</TableCell>
                  <TableCell>Assignment</TableCell>
                  <TableCell align="right"> </TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {(board.data ?? []).map((row) => (
                  <TableRow key={row.id}>
                    <TableCell>{row.studentName}</TableCell>
                    <TableCell>{assignmentSummary(row)}</TableCell>
                    <TableCell align="right">
                      <Button size="small" disabled={busy} onClick={() => clearRow(row.id)}>
                        Clear
                      </Button>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </Box>
      </Box>
    </Box>
  );
}
