const ROUTE: Record<string, string> = {
  po: "PO",
  oral: "PO",
  "by mouth": "PO",
  iv: "IV",
  im: "IM",
  sc: "SC",
  sq: "SC",
  subcut: "SC",
  subcutaneous: "SC",
  topical: "TOP",
  inh: "INH",
  inhaled: "INH",
  sl: "SL",
  pr: "PR",
  ou: "OU",
  os: "OS",
  od: "OD",
};

const FREQUENCY: Array<[RegExp, string]> = [
  [/\b(twice daily|twice a day|bid|b\.i\.d\.?)\b/i, "BID"],
  [/\b(three times daily|3 times daily|tid|t\.i\.d\.?)\b/i, "TID"],
  [/\b(four times daily|4 times daily|qid|q\.i\.d\.?)\b/i, "QID"],
  [/\b(once daily|once a day|(?<!\w)daily(?!\w)|q\.?\s*d\.?|(?<!\w)qd(?!\w))\b/i, "QD"],
  [/\b(at bedtime|every night|qhs|q\.?h\.?s\.?)\b/i, "QHS"],
  [/\b(every morning|qam|q\.?a\.?m\.?)\b/i, "QAM"],
  [/\b(every evening|qpm|q\.?p\.?m\.?)\b/i, "QPM"],
  [/\b(as needed|prn|p\.r\.n\.?)\b/i, "PRN"],
];

function routeLabel(value: string): string {
  const cleaned = value.trim();
  if (!cleaned) return "";
  return ROUTE[cleaned.toLowerCase()] ?? (cleaned.length <= 4 ? cleaned.toUpperCase() : cleaned);
}

function frequencyLabel(value: string): string {
  const cleaned = value.trim();
  if (!cleaned) return "";
  const parts: string[] = [];
  const every = cleaned.match(/(?:every\s*(\d+)\s*hours?|q(\d+)h)/i);
  if (every) parts.push(`Q${every[1] || every[2]}H`);
  for (const [pattern, label] of FREQUENCY) {
    if (label === "PRN" && pattern.test(cleaned)) {
      parts.push("PRN");
      break;
    }
    if (!parts.length && pattern.test(cleaned)) return label;
  }
  if (parts.length) return parts.join(" ");
  return cleaned;
}

/** Pharmacy-style SIG from dose + route + frequency, e.g. "10 mg PO QD". */
export function medicationSig(dose?: string | null, route?: string | null, frequency?: string | null): string {
  return [dose?.trim(), routeLabel(route ?? ""), frequencyLabel(frequency ?? "")].filter(Boolean).join(" ");
}
