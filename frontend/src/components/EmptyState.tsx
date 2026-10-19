import type { ReactNode } from "react";
import { Box, Typography } from "@mui/material";

export default function EmptyState({ title, children, action }: { title: string; children?: ReactNode; action?: ReactNode }) {
  return (
    <Box
      role="status"
      sx={{
        border: "1px dashed",
        borderColor: "divider",
        borderRadius: 1,
        p: { xs: 3, sm: 4 },
        textAlign: "center",
        bgcolor: "action.hover",
        maxWidth: 520,
        mx: "auto",
      }}
    >
      <Typography variant="subtitle1" component="p" sx={{ fontWeight: 700 }}>{title}</Typography>
      {children && (
        <Typography variant="body2" color="text.secondary" sx={{ mt: 0.75, maxWidth: "48ch", mx: "auto" }}>
          {children}
        </Typography>
      )}
      {action && <Box sx={{ mt: 2.5 }}>{action}</Box>}
    </Box>
  );
}
