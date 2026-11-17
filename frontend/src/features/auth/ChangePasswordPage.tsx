import { useState, type FormEvent } from "react";
import {
  Alert, Box, Button, IconButton, InputAdornment, Stack, TextField, Typography,
} from "@mui/material";
import VisibilityOutlined from "@mui/icons-material/VisibilityOutlined";
import VisibilityOffOutlined from "@mui/icons-material/VisibilityOffOutlined";
import { useNavigate } from "react-router-dom";
import { changePassword } from "../../api/auth";
import { homePathFor } from "../../utils/permissions";
import BrandLogo from "../../components/BrandLogo";
import { brandAtmosphere, utep } from "../../theme/tokens";
import { useSession } from "./useSession";

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
        navigate(activeRole === "patient" ? homePathFor("patient") : courseId ? homePathFor(activeRole) : "/select-course", { replace: true });
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
    <Box
      sx={{
        minHeight: "100dvh",
        display: "grid",
        gridTemplateColumns: { xs: "1fr", md: "minmax(0, 1fr) minmax(320px, 440px)" },
        bgcolor: utep.navyDark,
      }}
    >
      <Box
        sx={{
          display: { xs: "none", md: "flex" },
          flexDirection: "column",
          justifyContent: "flex-end",
          px: 7,
          py: 7,
          backgroundImage: brandAtmosphere,
          color: "#fff",
        }}
      >
        <BrandLogo variant="hero" titleSize={48} />
        <Box sx={{ width: 64, height: 3, bgcolor: utep.orange, my: 2 }} />
        <Typography sx={{ opacity: 0.85 }}>Set your own password before opening a chart.</Typography>
        <Box sx={{ mt: 4, maxWidth: 240, opacity: 0.9 }}>
          <BrandLogo variant="wordmark" />
        </Box>
      </Box>

      <Box
        component="main"
        sx={{
          bgcolor: utep.paper,
          display: "flex",
          flexDirection: "column",
          justifyContent: "center",
          px: { xs: 3, sm: 4 },
          py: 5,
        }}
      >
        <Box sx={{ display: "flex", mb: 3 }}>
          <Box sx={{ flex: 1 }} />
          <Button onClick={signOut} size="small">Sign out</Button>
        </Box>
        <Box component="section" aria-labelledby="password-title" sx={{ width: "100%", maxWidth: 360, mx: "auto" }}>
          <Typography id="password-title" component="h1" variant="h5" sx={{ mb: 0.75 }}>
            Choose a new password
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
            This account is still using a temporary password.
          </Typography>

          {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}

          <Box component="form" noValidate onSubmit={submit}>
            <Stack spacing={2}>
              <TextField
                label="Temporary password" type={showCurrent ? "text" : "password"} autoComplete="current-password" autoFocus fullWidth size="medium"
                value={currentPassword} onChange={(e) => setCurrentPassword(e.target.value)}
                slotProps={{ input: { endAdornment: eye(showCurrent, () => setShowCurrent((s) => !s), "Show temporary password", "Hide temporary password") } }}
              />
              <TextField
                label="New password" type={showNew ? "text" : "password"} autoComplete="new-password" fullWidth size="medium"
                value={newPassword} onChange={(e) => setNewPassword(e.target.value)}
                helperText="At least 8 characters"
                slotProps={{ input: { endAdornment: eye(showNew, () => setShowNew((s) => !s), "Show new password", "Hide new password") } }}
              />
              <TextField
                label="Confirm new password" type={showNew ? "text" : "password"} autoComplete="new-password" fullWidth size="medium"
                value={confirm} onChange={(e) => setConfirm(e.target.value)}
              />
              <Button type="submit" variant="contained" size="large" disabled={busy}>
                {busy ? "Saving…" : "Save password"}
              </Button>
            </Stack>
          </Box>
        </Box>
      </Box>
    </Box>
  );
}
