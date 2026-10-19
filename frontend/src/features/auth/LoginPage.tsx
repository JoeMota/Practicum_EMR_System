import { useState, type FormEvent } from "react";
import {
  Alert, Box, Button, IconButton, InputAdornment, Paper, Stack, TextField, Typography,
} from "@mui/material";
import VisibilityOutlined from "@mui/icons-material/VisibilityOutlined";
import VisibilityOffOutlined from "@mui/icons-material/VisibilityOffOutlined";
import { useNavigate } from "react-router-dom";
import { login } from "../../api/auth";
import { takeSignedOutNotice } from "../../api/client";
import { homePathFor } from "../../utils/permissions";
import { trainingStripe, utep } from "../../theme/tokens";
import { useAuth } from "./AuthContext";

export default function LoginPage() {
  const navigate = useNavigate();
  const { signIn } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState("");
  const [notice] = useState(takeSignedOutNotice);
  const [busy, setBusy] = useState(false);

  const submit = (e: FormEvent) => {
    e.preventDefault();
    if (!email.trim()) {
      setError("Enter your UTEP email to continue.");
      return;
    }
    if (!password) {
      setError("Enter your password.");
      return;
    }
    setBusy(true);
    setError("");
    login(email, password)
      .then((result) => {
        signIn(result.user, result.accessToken, result.mustChangePassword);
        if (result.mustChangePassword) {
          navigate("/change-password", { replace: true });
          return;
        }
        const oneRoleOneCourse = result.user.roles.length === 1 && result.user.roles[0].courseIds.length === 1;
        navigate(oneRoleOneCourse ? homePathFor(result.user.roles[0].role) : "/select-course", { replace: true });
      })
      .catch((err: Error) => setError(err.message))
      .finally(() => setBusy(false));
  };

  return (
    <Box sx={{ minHeight: "100dvh", bgcolor: "background.default", display: "flex", flexDirection: "column" }}>
      <Box component="header" sx={{ bgcolor: utep.orange, color: utep.navy, px: { xs: 2, sm: 3.5 }, height: 60, display: "flex", alignItems: "center" }}>
        <Typography component="span" sx={{ fontWeight: 800, fontSize: 18 }}>UTEP EMR</Typography>
        <Typography component="span" sx={{ ml: 1.5, fontWeight: 600, fontSize: 13, opacity: 0.85, display: { xs: "none", sm: "inline" } }}>
          Educational medical record
        </Typography>
      </Box>
      <Box aria-hidden sx={{ height: 6, background: trainingStripe }} />

      <Box component="main" sx={{ flex: 1, display: "grid", placeItems: "center", px: 2, py: 5 }}>
        <Paper component="section" aria-labelledby="login-title" sx={{ width: "100%", maxWidth: 420, p: { xs: 3, sm: 4 } }}>
          <Typography id="login-title" component="h1" variant="h5" sx={{ mb: 0.5 }}>Sign in</Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
            For UTEP health sciences students and faculty. Every patient here is simulated training data — never real PHI.
          </Typography>

          {notice && <Alert severity="info" sx={{ mb: 2 }}>{notice}</Alert>}
          {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}

          <Box component="form" noValidate onSubmit={submit}>
            <Stack spacing={2}>
              <TextField
                label="UTEP email" type="email" autoComplete="username" autoFocus fullWidth
                placeholder="you@miners.utep.edu" value={email} onChange={(e) => setEmail(e.target.value)}
              />
              <TextField
                label="Password" type={showPassword ? "text" : "password"} autoComplete="current-password"
                fullWidth value={password} onChange={(e) => setPassword(e.target.value)}
                slotProps={{ input: {
                  endAdornment: (
                    <InputAdornment position="end">
                      <IconButton
                        aria-label={showPassword ? "Hide password" : "Show password"}
                        onClick={() => setShowPassword((s) => !s)} edge="end"
                      >
                        {showPassword ? <VisibilityOffOutlined /> : <VisibilityOutlined />}
                      </IconButton>
                    </InputAdornment>
                  ),
                } }}
              />
              <Button type="submit" variant="contained" size="large" disabled={busy}>
                {busy ? "Signing in…" : "Sign in"}
              </Button>
              {import.meta.env.DEV && (
                <Alert severity="info" icon={false}>
                  <Typography variant="subtitle2" sx={{ mb: 0.5 }}>Demo accounts</Typography>
                  <Typography variant="body2" component="div">
                    Student: <Box component="code" sx={{ fontFamily: "inherit", fontWeight: 700 }}>daniel.reyes@miners.utep.edu</Box>
                    <br />
                    Instructor: <Box component="code" sx={{ fontFamily: "inherit", fontWeight: 700 }}>gerardo.sillas@utep.edu</Box>
                    <br />
                    Password <Box component="code" sx={{ fontFamily: "inherit", fontWeight: 700 }}>practicum-demo</Box>
                  </Typography>
                </Alert>
              )}
            </Stack>
          </Box>
        </Paper>
      </Box>
    </Box>
  );
}
