import { useState } from "react";
import { Box, Button, Collapse, Typography } from "@mui/material";
import { useSession } from "../auth/useSession";
import { useAsync } from "../../utils/useAsync";
import { assignmentSummary, listSimLabRooms, mySimLabAssignments } from "../../api/simLab";
import { utep } from "../../theme/tokens";
import LabFloorMap from "./LabFloorMap";

function todayISO() {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
}

/** Quiet strip: assignment + optional map. Hidden when nothing is assigned. */
export default function LabAssignmentStrip() {
  const { activeRole, courseId } = useSession();
  const [open, setOpen] = useState(false);
  const day = todayISO();

  const mine = useAsync(
    () => (activeRole === "student" && courseId
      ? mySimLabAssignments(courseId, activeRole, day)
      : Promise.resolve([])),
    [activeRole, courseId, day],
  );
  const rooms = useAsync(
    () => (activeRole === "student" && courseId && (mine.data?.length ?? 0) > 0
      ? listSimLabRooms(courseId, activeRole)
      : Promise.resolve([])),
    [activeRole, courseId, mine.data],
  );

  const row = mine.data?.[0];
  if (activeRole !== "student" || !courseId || !row) return null;

  const summary = assignmentSummary(row);

  return (
    <Box
      sx={{
        mb: 2,
        border: `1px solid ${utep.line}`,
        borderRadius: 1.5,
        bgcolor: utep.paper,
        px: { xs: 1.5, md: 2 },
        py: 1,
      }}
    >
      <Box sx={{ display: "flex", alignItems: "center", gap: 1.5, flexWrap: "wrap" }}>
        <Typography sx={{ color: utep.ink2, fontSize: 13, fontWeight: 600, flex: "1 1 auto" }}>
          Your lab today · {summary}
        </Typography>
        <Button
          size="small"
          onClick={() => setOpen((v) => !v)}
          sx={{ textTransform: "none", color: utep.navy, fontWeight: 600 }}
        >
          {open ? "Hide map" : "Show map"}
        </Button>
      </Box>
      <Collapse in={open}>
        <Box sx={{ pt: 1.25 }}>
          <LabFloorMap rooms={rooms.data ?? []} highlightNumber={row.room.number} />
        </Box>
      </Collapse>
    </Box>
  );
}
