import { describe, expect, it } from "vitest";
import { compileNarrative } from "./generalSoap";
import type { Patient } from "../../types";

const patient = {
  chiefComplaint: "Chest pain",
  vitals: [{ label: "BP", value: "146/88", status: "recorded" }],
} as Patient;

describe("compileNarrative", () => {
  it("builds a readable SOAP narrative from structured fields", () => {
    const text = compileNarrative(
      patient,
      {
        cc: "Chest pain",
        hpi_mnemonic: "oldcarts",
        hpi_oldcarts: JSON.stringify({
          onset: "Yesterday",
          location: "Left chest",
          duration: "2 hours",
          character: "Pressure",
          aggravating: "Walking",
          alleviating: "Rest",
          radiation: "None",
          timing: "Intermittent",
          severity: "6/10",
        }),
        ros_mode: "focused",
        ros_checks: JSON.stringify({ cardiovascular: "positive", respiratory: "negative" }),
        exam: "Alert, no distress",
        problem_plans: JSON.stringify({
          I10: { medications: "Continue lisinopril", education: "Home BP log", followUp: "2 weeks", referrals: "" },
        }),
      },
      [{ code: "I10", label: "Essential hypertension", rationale: "Elevated readings" }],
    );

    expect(text).toContain("SUBJECTIVE");
    expect(text).toContain("Chest pain");
    expect(text).toContain("OLDCARTS");
    expect(text).toContain("I10");
    expect(text).toContain("Continue lisinopril");
  });
});
