/** In-app course rubrics keyed by the course `rubricFileName`. */

export interface RubricCriterion {
  id: string;
  label: string;
  detail: string;
}

export interface CourseRubric {
  title: string;
  fileName: string;
  overview: string;
  criteria: RubricCriterion[];
}

const SOAP_RUBRIC: CourseRubric = {
  title: "SOAP note rubric — PHAR 5320",
  fileName: "SOAP-note-rubric.pdf",
  overview: "Use this checklist when writing or co-signing assessment SOAP notes. Each section should be specific to this patient and visit.",
  criteria: [
    {
      id: "s",
      label: "Subjective",
      detail: "Chief concern, HPI (onset, timing, severity), relevant ROS, adherence, and social context that affect the plan.",
    },
    {
      id: "o",
      label: "Objective",
      detail: "Vitals, exam findings, labs/imaging reviewed, and current medications with doses — pulled from the chart when available.",
    },
    {
      id: "a",
      label: "Assessment",
      detail: "Prioritized problem list with working diagnoses or drug-therapy problems; links findings to each problem.",
    },
    {
      id: "p",
      label: "Plan",
      detail: "Actionable plan per problem (monitor, adjust, educate, refer). Includes follow-up timing and patient counseling points.",
    },
    {
      id: "safety",
      label: "Safety & professionalism",
      detail: "Allergy and interaction checks noted, no fabricated data, clear attribution, and appropriate language for the record.",
    },
  ],
};

const PT_RUBRIC: CourseRubric = {
  title: "PT daily note rubric — PHYT 6310",
  fileName: "PT-daily-note-rubric.pdf",
  overview: "Use this checklist for physical therapy daily notes. Document skilled care, objective measures, and the plan for the next visit.",
  criteria: [
    {
      id: "subjective",
      label: "Patient report",
      detail: "Patient-reported symptoms, functional limits, and response to the prior session.",
    },
    {
      id: "objective",
      label: "Skilled interventions & measures",
      detail: "Interventions performed, assistance level, objective measures (ROM, strength, gait), and time/intensity when relevant.",
    },
    {
      id: "assessment",
      label: "Clinical reasoning",
      detail: "Interpretation of progress toward goals; skilled need for continued therapy is clear.",
    },
    {
      id: "plan",
      label: "Plan of care",
      detail: "Next-session focus, progression or regression, HEP updates, and communication with the care team if needed.",
    },
    {
      id: "safety",
      label: "Safety & documentation standards",
      detail: "Precautions addressed, no copy-forward errors, and language appropriate for medical-legal review.",
    },
  ],
};

const BY_FILE: Record<string, CourseRubric> = {
  [SOAP_RUBRIC.fileName]: SOAP_RUBRIC,
  [PT_RUBRIC.fileName]: PT_RUBRIC,
};

export function rubricForFile(fileName?: string | null): CourseRubric | undefined {
  if (!fileName) return undefined;
  return BY_FILE[fileName];
}
