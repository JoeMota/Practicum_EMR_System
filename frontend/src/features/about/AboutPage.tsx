import { Box, Typography } from "@mui/material";
import clarissa from "../../assets/team/clarissa.jpg";
import daniel from "../../assets/team/daniel.jpg";
import gerardo from "../../assets/team/gerardo.jpg";
import joe from "../../assets/team/joe.jpg";
import { usePageHeading } from "../../components/usePageHeading";
import { utep } from "../../theme/tokens";

const TEAM = [
  { name: "Clarissa Dominguez", photo: clarissa, focus: "center 20%" },
  { name: "Daniel Reyes", photo: daniel, focus: "center 28%" },
  { name: "Gerardo Sillas", photo: gerardo, focus: "center 32%" },
  { name: "Joe Mota", photo: joe, focus: "center 22%" },
];

export default function AboutPage() {
  usePageHeading("About us");

  return (
    <Box sx={{ maxWidth: 1120, mx: "auto", py: { xs: 1, md: 2 } }}>
      <Box sx={{ textAlign: "center", maxWidth: 680, mx: "auto", mb: { xs: 3, md: 4.5 } }}>
        <Typography
          component="h2"
          sx={{
            color: utep.navy, fontWeight: 700, letterSpacing: "-0.03em", lineHeight: 1.15,
            fontSize: { xs: 34, md: 48 },
          }}
        >
          Meet the team
        </Typography>
        <Typography sx={{ mt: 1.5, color: utep.ink2, fontSize: { xs: 15, md: 17 }, lineHeight: 1.6 }}>
          We are master's students in artificial intelligence at UTEP, graduating in December 2026.
        </Typography>
      </Box>

      <Box
        sx={{
          display: "grid",
          gap: 2.5,
          gridTemplateColumns: { xs: "1fr", sm: "1fr 1fr", lg: "repeat(4, 1fr)" },
        }}
      >
        {TEAM.map((person) => (
          <Box
            key={person.name}
            sx={{
              position: "relative",
              borderRadius: "18px",
              overflow: "hidden",
              bgcolor: utep.navy,
              border: `1px solid ${utep.line}`,
              minHeight: 420,
            }}
          >
            <Box
              component="img"
              src={person.photo}
              alt=""
              sx={{
                display: "block",
                width: "100%",
                height: 420,
                objectFit: "cover",
                objectPosition: person.focus,
              }}
            />
            <Box
              sx={{
                position: "absolute",
                left: 12,
                right: 12,
                bottom: 12,
                bgcolor: "#fff",
                borderRadius: "12px",
                px: 1.75,
                py: 1.35,
                borderTop: `3px solid ${utep.orange}`,
                boxShadow: "0 10px 24px rgba(14, 34, 80, 0.16)",
              }}
            >
              <Typography sx={{ fontWeight: 700, color: utep.navy, fontSize: 16, lineHeight: 1.3 }}>
                {person.name}
              </Typography>
              <Typography sx={{ color: utep.ink2, fontSize: 13, mt: 0.25 }}>
                M.S. Artificial Intelligence
              </Typography>
            </Box>
          </Box>
        ))}
      </Box>
    </Box>
  );
}
