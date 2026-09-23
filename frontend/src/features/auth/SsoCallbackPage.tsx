import { useEffect, useState } from "react";
import { Alert, Box, CircularProgress, Typography } from "@mui/material";
import { useNavigate, useSearchParams } from "react-router-dom";
import { completeSsoSession } from "../../api/auth";
import { homePathFor } from "../../utils/permissions";
import { utep } from "../../theme/tokens";
import { useAuth } from "./AuthContext";

/** Handles redirects from Entra SSO or Duo Universal Prompt. */
export default function SsoCallbackPage() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const { signIn } = useAuth();
  const [error, setError] = useState("");

  useEffect(() => {
    const token = searchParams.get("access_token");
    if (!token) {
      setError("Missing access token from UTEP login.");
      return;
    }
    let cancelled = false;
    (async () => {
      try {
        const user = await completeSsoSession(token);
        if (cancelled) return;
        signIn(user);
        if (user.mustChangePassword) {
          navigate("/change-password", { replace: true });
          return;
        }
        const oneRoleOneCourse = user.roles.length === 1 && user.roles[0].courseIds.length === 1;
        navigate(oneRoleOneCourse ? homePathFor(user.roles[0].role) : "/select-course", { replace: true });
      } catch (e) {
        if (!cancelled) setError((e as Error).message || "Could not finish UTEP sign-in.");
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [searchParams, navigate, signIn]);

  return (
    <Box sx={{ minHeight: "100dvh", bgcolor: "background.default", display: "grid", placeItems: "center", px: 2 }}>
      <Box sx={{ textAlign: "center", maxWidth: 420 }}>
        <Typography sx={{ fontWeight: 800, color: utep.navy, mb: 2 }}>UTEP EMR</Typography>
        {error ? (
          <Alert severity="error">{error}</Alert>
        ) : (
          <>
            <CircularProgress size={28} sx={{ mb: 2 }} />
            <Typography color="text.secondary">Finishing UTEP sign-in…</Typography>
          </>
        )}
      </Box>
    </Box>
  );
}
