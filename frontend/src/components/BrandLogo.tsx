import { Box, Typography, type BoxProps } from "@mui/material";
import pickMark from "../assets/brand/utep-pick-mark.svg";
import pick from "../assets/brand/utep-pick.svg";
import wordmark from "../assets/brand/utep-wordmark.svg";
import { fontDisplay, utep } from "../theme/tokens";

type Variant = "mark" | "lockup" | "hero" | "wordmark";

type Props = {
  variant?: Variant;
  /** Side-nav collapsed: mark only. */
  compact?: boolean;
  subtitle?: string;
  invert?: boolean;
  /** Hero product title size (px or CSS length). */
  titleSize?: { xs?: number | string; sm?: number | string; md?: number | string } | number | string;
} & BoxProps;

/**
 * Official UTEP pick mark + product lockup.
 * Mark/wordmark assets come from utep.edu public brand files.
 */
export default function BrandLogo({
  variant = "lockup",
  compact = false,
  subtitle = "Training",
  invert = false,
  titleSize,
  sx,
  ...rest
}: Props) {
  if (variant === "mark" || compact) {
    return (
      <Box
        component="img"
        src={pickMark}
        alt=""
        aria-hidden
        sx={{ width: 34, height: 34, display: "block", borderRadius: 0.75, flexShrink: 0, ...sx }}
        {...rest}
      />
    );
  }

  if (variant === "wordmark") {
    return (
      <Box
        component="img"
        src={wordmark}
        alt="The University of Texas at El Paso"
        sx={{ display: "block", width: "100%", maxWidth: 280, height: "auto", ...sx }}
        {...rest}
      />
    );
  }

  if (variant === "hero") {
    const size = titleSize ?? { xs: 40, sm: 52, md: 64 };
    return (
      <Box sx={{ ...sx }} {...rest}>
        <Box
          component="img"
          src={pick}
          alt=""
          aria-hidden
          sx={{ width: { xs: 44, md: 56 }, height: "auto", display: "block", mb: 2.5 }}
        />
        <Typography
          component="p"
          sx={{
            fontFamily: fontDisplay,
            fontWeight: 800,
            fontSize: size,
            lineHeight: 0.95,
            letterSpacing: "-0.04em",
            color: invert ? utep.navy : "#fff",
            mb: 1.5,
          }}
        >
          UTEP EMR
        </Typography>
      </Box>
    );
  }

  return (
    <Box sx={{ display: "flex", alignItems: "center", gap: 1.25, ...sx }} {...rest}>
      <Box
        component="img"
        src={pickMark}
        alt=""
        aria-hidden
        sx={{ width: 34, height: 34, display: "block", borderRadius: 0.75, flexShrink: 0 }}
      />
      <Box>
        <Typography
          sx={{
            color: invert ? utep.navy : "#fff",
            fontFamily: fontDisplay,
            fontWeight: 750,
            fontSize: 17,
            lineHeight: 1.15,
            letterSpacing: "-0.02em",
          }}
        >
          UTEP EMR
        </Typography>
        {subtitle ? (
          <Typography variant="caption" sx={{ color: invert ? utep.ink2 : "rgba(255,255,255,0.65)" }}>
            {subtitle}
          </Typography>
        ) : null}
      </Box>
    </Box>
  );
}
