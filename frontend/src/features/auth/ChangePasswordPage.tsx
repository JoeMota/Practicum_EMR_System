import { useState, type FormEvent } from "react";
import {
  Alert, Box, Button, IconButton, InputAdornment, Paper, Stack, TextField, Typography,
} from "@mui/material";
import VisibilityOutlined from "@mui/icons-material/VisibilityOutlined";
import VisibilityOffOutlined from "@mui/icons-material/VisibilityOffOutlined";
import { useNavigate } from "react-router-dom";
import { changePassword } from "../../api/auth";
import { homePathFor } from "../../utils/permissions";
import { trainingStripe, utep } from "../../theme/tokens";
import { useSession } from "./AuthContext";

export default function ChangePasswordPage() {
  const navigate = useNavigate();
  const { activeRole, courseId, clearPasswordChange, signOut } = useSession();
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [showCurrent, setShowCurrent] = useState(false);
  const [showNew, setShowNew] = useState(false);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const submit = (e: FormEvent) => {
    e.preventDefault();
    if (!currentPassword) {
      setError("Enter your current temporary password.");
      return;
    }
    if (newPassword.length < 8) {
      setError("Use at least 8 characters.");
      return;
    }
    if (newPassword !== confirm) {
      setError("The new passwords don't match.");
      return;
    }
    if (newPassword === currentPassword) {
      setError("New password must be different.");
      return;
    }
    setBusy(true);
    setError("");
    changePassword(currentPassword, newPassword)
      .then(() => {
        clearPasswordChange();
        navigate(courseId ? homePathFor(activeRole) : "/select-course", { replace: true });
      })
      .catch((err: Error) => setError(err.message))
      .finally(() => setBusy(false));
  };

  const eye = (shown: boolean, toggle: () => void, labelShow: string, labelHide: string) => (
    <InputAdornment position="end">
      <IconButton aria-label={shown ? labelHide : labelShow} onClick={toggle} edge="end">
        {shown ? <VisibilityOffOutlined /> : <VisibilityOutlined />}
      </IconButton>
    </InputAdornment>
  );

  return (
    <Box sx={{ minHeight: "100dvh", bgcolor: "background.default", display: "flex", flexDirection: "column" }}>
      <Box component="header" sx={{ bgcolor: utep.orange, color: utep.navy, px: { xs: 2, sm: 3.5 }, height: 60, display: "flex", alignItems: "center" }}>
        <Typography component="span" sx={{ fontWeight: 800, fontSize: 18 }}>UTEP EMR</Typography>
        <Box sx={{ flex: 1 }} />
        <Button color="inherit" onClick={signOut}>Sign out</Button>
      </Box>
      <Box aria-hidden sx={{ height: 6, background: trainingStripe }} />

      <Box component="main" sx={{ flex: 1, display: "grid", placeItems: "center", px: 2, py: 5 }}>
        <Paper component="section" aria-labelledby="password-title" sx={{ width: "100%", maxWidth: 420, p: { xs: 3, sm: 4 } }}>
          <Typography id="password-title" component="h1" variant="h5" sx={{ mb: 0.5 }}>Choose a new password</Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
            This account is still using a temporary password. Set your own before opening a chart.
          </Typography>

          {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}

          <Box component="form" noValidate onSubmit={submit}>
            <Stack spacing={2}>
              <TextField
                label="Temporary password" type={showCurrent ? "text" : "password"} autoComplete="current-password" autoFocus fullWidth
                value={currentPassword} onChange={(e) => setCurrentPassword(e.target.value)}
                slotProps={{ input: { endAdornment: eye(showCurrent, () => setShowCurrent((s) => !s), "Show temporary password", "Hide temporary password") } }}
              />
              <TextField
                label="New password" type={showNew ? "text" : "password"} autoComplete="new-password" fullWidth
                value={newPassword} onChange={(e) => setNewPassword(e.target.value)}
                helperText="At least 8 characters"
                slotProps={{ input: { endAdornment: eye(showNew, () => setShowNew((s) => !s), "Show new password", "Hide new password") } }}
              />
              <TextField
                label="Confirm new password" type={showNew ? "text" : "password"} autoComplete="new-password" fullWidth
                value={confirm} onChange={(e) => setConfirm(e.target.value)}
              />
              <Button type="submit" variant="contained" size="large" disabled={busy}>
                {busy ? "Saving…" : "Save password"}
              </Button>
            </Stack>
          </Box>
        </Paper>
      </Box>
    </Box>
  );
}
