import { useRef, useState } from "react";
import { Alert, Button, Typography } from "@mui/material";
import { uploadCaseRubric } from "../../api/cases";
import CourseRubricPanel from "../encounters/components/CourseRubricPanel";
import type { GradingGuide, Role } from "../../types";

export default function CaseRubricPanel({ role, caseId, initial }: { role: Role; caseId: string; initial?: GradingGuide | null }) {
  const fileInput = useRef<HTMLInputElement>(null);
  const [guide, setGuide] = useState<GradingGuide | null>(initial ?? null);
  const [error, setError] = useState("");

  return (
    <>
      <Typography component="h2" variant="h6">Case rubric</Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
        Students do not see this rubric. If you leave it blank, the instructor uses the course rubric when grading. Scores stay off the student view.
      </Typography>
      <input
        ref={fileInput}
        hidden
        type="file"
        accept=".pdf,.docx,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        onChange={async (event) => {
          const file = event.target.files?.[0];
          event.target.value = "";
          if (!file) return;
          setError("");
          try {
            setGuide(await uploadCaseRubric(role, caseId, file));
          } catch (e) {
            setError((e as Error).message);
          }
        }}
      />
      <Button variant="outlined" onClick={() => fileInput.current?.click()}>Upload PDF or Word rubric</Button>
      {error && <Alert severity="error" sx={{ mt: 1.5 }}>{error}</Alert>}
      <CourseRubricPanel guide={guide ? { ...guide, source: "case" } : null} title="Case rubric" />
    </>
  );
}
