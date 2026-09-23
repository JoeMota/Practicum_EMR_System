import { useState, type FormEvent } from "react";
import {
  Alert, Box, Button, IconButton, InputAdornment, Link, Paper, Stack, TextField, Typography,
} from "@mui/material";
import VisibilityOutlined from "@mui/icons-material/VisibilityOutlined";
import VisibilityOffOutlined from "@mui/icons-material/VisibilityOffOutlined";
import SmsOutlined from "@mui/icons-material/SmsOutlined";
import MailOutlineRounded from "@mui/icons-material/MailOutlineRounded";
import { useNavigate } from "react-router-dom";
import { DEV_CODE, sendCode, startSignIn, verifyCode, type CodeChannel } from "../../api/auth";
import { homePathFor } from "../../utils/permissions";
import { utep } from "../../theme/tokens";
import { useAuth } from "./AuthContext";

type Step = "credentials" | "channel" | "code";

export default function LoginPage() {
  const navigate = useNavigate();
  const { signIn } = useAuth();

  const [step, setStep] = useState<Step>("credentials");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [challenge, setChallenge] = useState<{ id: string; phoneLast4?: string; emailMasked: string }>();
  const [channel, setChannel] = useState<CodeChannel>("sms");
  const [code, setCode] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function run(fn: () => Promise<void>) {
    setBusy(true);
    setError("");
    try {
      await fn();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  const submitCredentials = (e: FormEvent) => {
    e.preventDefault();
    if (!email.trim()) return setError("Enter your UTEP email to continue.");
    run(async () => {
      const res = await startSignIn(email, password);
      setChallenge({ id: res.challengeId, phoneLast4: res.phoneLast4, emailMasked: res.emailMasked });
      setStep("channel");
    });
  };

  const chooseChannel = (c: CodeChannel) =>
    run(async () => {
      setChannel(c);
      await sendCode(challenge!.id, c);
      setStep("code");
    });

  const submitCode = (e: FormEvent) => {
    e.preventDefault();
    run(async () => {
      const user = await verifyCode(challenge!.id, code.trim());
      signIn(user);
      if (user.mustChangePassword) {
        navigate("/change-password", { replace: true });
        return;
      }
      const oneRoleOneCourse = user.roles.length === 1 && user.roles[0].courseIds.length === 1;
      navigate(oneRoleOneCourse ? homePathFor(user.roles[0].role) : "/select-course", { replace: true });
    });
  };

  const destination =
    channel === "sms" ? `your phone ending in ${challenge?.phoneLast4}` : challenge?.emailMasked;

  return (
    <Box sx={{ minHeight: "100dvh", bgcolor: "background.default", display: "flex", flexDirection: "column" }}>
      <Box component="header" sx={{ bgcolor: utep.orange, color: utep.navy, px: { xs: 2, sm: 3.5 }, height: 60, display: "flex", alignItems: "center" }}>
        <Typography component="span" sx={{ fontWeight: 800, fontSize: 18 }}>UTEP EMR</Typography>
      </Box>

      <Box component="main" sx={{ flex: 1, display: "grid", placeItems: "center", px: 2, py: 5 }}>
        <Paper component="section" aria-labelledby="login-title" sx={{ width: "100%", maxWidth: 420, p: { xs: 3, sm: 4 } }}>
          <Typography id="login-title" component="h1" variant="h5" sx={{ mb: 0.5 }}>
            {step === "credentials" ? "Sign in" : step === "channel" ? "Verify it's you" : "Enter your code"}
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
            {step === "credentials" && "For UTEP health sciences students and faculty. Every patient here is simulated."}
            {step === "channel" && "We'll send a 6-digit code. Choose where to get it."}
            {step === "code" && `We sent a 6-digit code to ${destination}.`}
          </Typography>

          {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}

          {step === "credentials" && (
            <Box component="form" noValidate onSubmit={submitCredentials}>
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
                  {busy ? "Checking…" : "Continue"}
                </Button>
              </Stack>
            </Box>
          )}

          {step === "channel" && (
            <Stack spacing={1.5}>
              {challenge?.phoneLast4 && (
                <Button variant="outlined" size="large" startIcon={<SmsOutlined />} disabled={busy}
                  onClick={() => chooseChannel("sms")} sx={{ justifyContent: "flex-start" }}>
                  Text me at •••-{challenge.phoneLast4}
                </Button>
              )}
              <Button variant="outlined" size="large" startIcon={<MailOutlineRounded />} disabled={busy}
                onClick={() => chooseChannel("email")} sx={{ justifyContent: "flex-start" }}>
                Email me at {challenge?.emailMasked}
              </Button>
              <Link component="button" type="button" variant="body2" onClick={() => setStep("credentials")} sx={{ alignSelf: "flex-start", mt: 1 }}>
                Use a different account
              </Link>
            </Stack>
          )}

          {step === "code" && (
            <Box component="form" noValidate onSubmit={submitCode}>
              <Stack spacing={2}>
                <TextField
                  label="6-digit code" autoFocus fullWidth value={code}
                  onChange={(e) => setCode(e.target.value.replace(/\D/g, "").slice(0, 6))}
                  slotProps={{ htmlInput: { inputMode: "numeric", autoComplete: "one-time-code", maxLength: 6, style: { letterSpacing: "0.4em", fontSize: 20 } } }}
                  helperText={import.meta.env.DEV ? `Dev / educational MFA code: ${DEV_CODE}` : undefined}
                />
                <Button type="submit" variant="contained" size="large" disabled={busy || code.length !== 6}>
                  {busy ? "Verifying…" : "Verify and sign in"}
                </Button>
                <Stack direction="row" spacing={2}>
                  <Link component="button" type="button" variant="body2" onClick={() => chooseChannel(channel)}>
                    Send a new code
                  </Link>
                  <Link component="button" type="button" variant="body2" onClick={() => setStep("channel")}>
                    Send it somewhere else
                  </Link>
                </Stack>
              </Stack>
            </Box>
          )}
        </Paper>
      </Box>
    </Box>
  );
}
