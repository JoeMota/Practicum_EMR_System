import * as XLSX from "xlsx";
import type { RosterRow } from "../../types";

const norm = (k: string) => k.toLowerCase().replace(/[^a-z0-9]/g, "");
const NAME = ["name", "fullname", "studentname"];
const FIRST = ["first", "firstname", "givenname"];
const LAST = ["last", "lastname", "surname", "familyname"];
const EMAIL = ["email", "emailaddress", "utepemail", "mineremail", "minersemail"];
const ID = ["universityid", "800number", "id", "studentid", "utepid", "800"];

function pick(row: Record<string, unknown>, keys: string[]): string {
  const hit = Object.keys(row).find((k) => keys.includes(norm(k)));
  return hit ? String(row[hit] ?? "").trim() : "";
}

export function validateRosterRow(row: RosterRow): RosterRow {
  let problem: string | undefined;
  if (!row.fullName) problem = "Missing name";
  else if (!/@(miners\.)?utep\.edu$/.test(row.email)) problem = "Email must be @miners.utep.edu or @utep.edu";
  else if (!/^800\d{6}$/.test(row.universityId)) problem = "ID must be a 9-digit 800 number";
  return { ...row, problem };
}

export async function parseRosterFile(file: File): Promise<RosterRow[]> {
  const wb = XLSX.read(await file.arrayBuffer());
  const sheet = wb.Sheets[wb.SheetNames[0]];
  const raw = XLSX.utils.sheet_to_json<Record<string, unknown>>(sheet, { defval: "" });
  const seen = new Set<string>();

  return raw
    .map((r) => {
      const fullName = pick(r, NAME) || [pick(r, FIRST), pick(r, LAST)].filter(Boolean).join(" ");
      return { fullName, email: pick(r, EMAIL).toLowerCase(), universityId: pick(r, ID) };
    })
    .filter((r) => r.fullName || r.email || r.universityId)
    .map((r) => {
      const validated = validateRosterRow(r);
      const problem = validated.problem ?? (seen.has(r.email) ? "Duplicate email in this file" : undefined);
      seen.add(r.email);
      return { ...validated, problem };
    });
}

export const ROSTER_TEMPLATE_CSV = "Name,Email,800 Number\nJane Student,jstudent@miners.utep.edu,800000000\n";
