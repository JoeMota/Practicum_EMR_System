import { Box, Button, Typography } from "@mui/material";
import { Link as RouterLink } from "react-router-dom";
import { useSession } from "../features/auth/AuthContext";
import { homePathFor } from "../utils/permissions";

export default function NotFoundPage() {
  const { activeRole } = useSession();
  const home = homePathFor(activeRole);
  const homeLabel =
    activeRole === "admin" ? "Go to roster"
      : activeRole === "instructor" || activeRole === "student" ? "Go to dashboard"
        : "Go to patients";

  return (
    <Box sx={{ py: 8, textAlign: "center" }}>
      <Typography component="h1" variant="h5">This page doesn't exist</Typography>
      <Typography color="text.secondary" sx={{ mb: 3, maxWidth: "42ch", mx: "auto" }}>
        The link may be outdated, or you don't have access to this screen in your current role.
      </Typography>
      <Button component={RouterLink} to={home} variant="contained">{homeLabel}</Button>
    </Box>
  );
}
