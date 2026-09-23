import { useState, type FormEvent } from "react";
import {
  Alert, Box, Button, IconButton, InputAdornment, Paper, Stack, TextField, Typography,
} from "@mui/material";
import VisibilityOutlined from "@mui/icons-material/VisibilityOutlined";
import VisibilityOffOutlined from "@mui/icons-material/VisibilityOffOutlined";
import { useNavigate } from "react-router-dom";
import { changePassword } from "../../api/auth";
import { homePathFor } from "../../utils/permissions";
import { utep } from "../../theme/tokens";
import { useSession } from "./AuthContext";

/** FR-08: temporary passwords must be changed before clinical access. */
export default function ChangePasswordPage() {
  const navigate = useNavigate();
  const { user, activeRole, courseId, markPasswordChanged, signOut } = useSession();
  const [currentPassword, setCurrent] = useState("");
  const [newPassword, setNew] = useState("");
  const [confirm, setConfirm] = useState("");
  const [show, setShow] = useState(false);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const submit = (e: FormEvent) => {
    e.preventDefault();
    if (newPassword.length < 8) return setError("New password must be at least 8 characters.");
    if (newPassword !== confirm) return setError("New password and confirmation don't match.");
    setBusy(true);
    setError("");
    changePassword(currentPassword, newPassword)
      .then(() => {
        markPasswordChanged();
        if (courseId) navigate(homePathFor(activeRole), { replace: true });
        else navigate("/select-course", { replace: true });
      })
      .catch((err: Error) => setError(err.message))
      .finally(() => setBusy(false));
  };

  return (
    <Box sx={{ minHeight: "100dvh", bgcolor: "background.default", display: "flex", flexDirection: "column" }}>
      <Box component="header" sx={{ bgcolor: utep.orange, color: utep.navy, px: { xs: 2, sm: 3.5 }, height: 60, display: "flex", alignItems: "center" }}>
        <Typography component="span" sx={{ fontWeight: 800, fontSize: 18 }}>UTEP EMR</Typography>
        <Box sx={{ flex: 1 }} />
        <Button color="inherit" onClick={signOut}>Sign out</Button>
      </Box>

      <Box component="main" sx={{ flex: 1, display: "grid", placeItems: "center", px: 2, py: 5 }}>
        <Paper component="section" aria-labelledby="pw-title" sx={{ width: "100%", maxWidth: 420, p: { xs: 3, sm: 4 } }}>
          <Typography id="pw-title" component="h1" variant="h5" sx={{ mb: 0.5 }}>
            Choose a new password
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
            Hi {user.fullName.split(" ")[0]} — your account still has a temporary password. Set a new one before opening patient charts.
          </Typography>

          {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}

          <Box component="form" noValidate onSubmit={submit}>
            <Stack spacing={2}>
              <TextField
                label="Current temporary password"
                type={show ? "text" : "password"}
                autoComplete="current-password"
                fullWidth
                value={currentPassword}
                onChange={(e) => setCurrent(e.target.value)}
                autoFocus
              />
              <TextField
                label="New password"
                type={show ? "text" : "password"}
                autoComplete="new-password"
                fullWidth
                value={newPassword}
                onChange={(e) => setNew(e.target.value)}
                helperText="At least 8 characters"
                slotProps={{
                  input: {
                    endAdornment: (
                      <InputAdornment position="end">
                        <IconButton aria-label={show ? "Hide password" : "Show password"} onClick={() => setShow((s) => !s)} edge="end">
                          {show ? <VisibilityOffOutlined /> : <VisibilityOutlined />}
                        </IconButton>
                      </InputAdornment>
                    ),
                  },
                }}
              />
              <TextField
                label="Confirm new password"
                type={show ? "text" : "password"}
                autoComplete="new-password"
                fullWidth
                value={confirm}
                onChange={(e) => setConfirm(e.target.value)}
              />
              <Button type="submit" variant="contained" size="large" disabled={busy}>
                {busy ? "Saving…" : "Save and continue"}
              </Button>
            </Stack>
          </Box>
        </Paper>
      </Box>
    </Box>
  );
}
