# Simulation Center Feedback — Implementation Plan

**Source:** [sim-center-feedback-summary.md](./sim-center-feedback-summary.md)  
**Code baseline:** surveyed against current `Patient` / chart / meds / sim models (Nov 2026)  
**Product direction (locked):** Keep the current **clinical EMR / sim-clinic** product Margie has already iterated on. Add sim-lab and clinical depth; do **not** reshape into a retail/PioneerRx product.

---

## Priority rules

1. **Do not regress** what she already liked (red allergies, med detail fields, SOAP, appointments display, photo banner, clinical overview).
2. **Do not re-litigate product setting** — Margie has already given multiple rounds of feedback; stay on the current clinical chart direction.
3. **Ship sim-lab gaps first** — students already take BP, lung sounds, counsel, and use rooms; the chart should match that.
4. **Retail ops (claims, barcode, labels) stay Deferred** — optional stretch only, not a direction change.
5. Prefer **simulated teaching flows** over real PBM/hardware integrations.
6. Prefer extending existing models/UI (Patient, Vital, Medication, MedicationAdministration, sim stations) over parallel systems.

---

## Current status snapshot

| Feedback item | Status now | Plan disposition |
|---|---|---|
| Patient photo | Present | Done — keep |
| Vitals history + BP entry | Present | Done — student + sim-nurse paths confirmed by tests |
| SOAP notes | Present | Done — keep |
| Allergies in red | Present | Done — keep |
| Med dose / route / freq / adherence / access-cost / indication / active | Present | Done — keep; optional SIG string later |
| ICD-10 on notes | Present | Done — keep; optional billing-education UI later |
| Room / unit / bed | Present | Done — keep |
| Emergency contact | Present | Done — banner, Overview, case editor |
| Appointments write API | Partial | Phase 1 — create/update if instructors need it for cases |
| HIPAA / consent | Present | Done — banner chip, Overview, case editor |
| DNR / advance directives | Present | Done — code status + advance notes on banner/Overview/case editor |
| Lung sounds documentation | Present | Done — Overview entry, case baseline, sim nurse path |
| Compounded medications | Present | Done — model, meds tab, case editor, Rosa seed example |
| Pharmacist fill → verify → release | Present | Done — MedicationOrder submit → verify/hold → release |
| SIG display helper | Present | Done — derived SIG on API + meds table |
| Educational claim / PBM simulation | Missing | Phase 3 — Deferred stretch |
| Med appearance photos | Missing | Phase 3 — Deferred stretch |
| Barcode scan workflow | Missing | Phase 3 — Deferred stretch |
| Rx label + leaflet | Missing | Phase 3 — Deferred stretch |
| PioneerRx / clinical-pharmacy UX reshape | Skipped | Out of scope — would change product too much |

---

## Phase 0 — Clarification & design

**Status: Skipped.**

Margie has already iterated with the team multiple times. We will not ask her to re-pick a pharmacy setting or redesign around PioneerRx. Phase 3 retail items remain Deferred stretch work, not gated on a new stakeholder cycle.

| ID | Backlog item | Status |
|---|---|---|
| P0-1 | Ask Margie: target setting | Cancelled |
| P0-2 | Ask Margie: realism depth / Phase 3 gate | Cancelled |
| P0-3 | PioneerRx + clinical pharmacy research notes | Cancelled |
| P0-4 | Finalize Phase 3 In/Out from Margie answers | Cancelled — Phase 3 stays Deferred |

---

## Phase 1 — Sim-lab chart completeness (highest priority)

**Goal:** Every current sim activity has a clear place in the chart, without changing the product shell Margie already approved.

### Backlog

| ID | Item | Priority | Effort | Why | Implementation sketch |
|---|---|---|---|---|---|
| P1-1 | Surface **emergency contact** on patient banner + Overview; add to case editor | P0 | S | She asked for it; data already exists | Wire `emergencyContact*` into frontend `Patient` type, `PatientBanner`, `SummaryTab`, `CaseEditorPage`; seed already has values |
| P1-2 | **Simulated HIPAA / consent** on file | P0 | M | Explicit ask; educational, not legal | Add `hipaa_on_file`, `hipaa_signed_at`, optional `hipaa_note` on `Patient` (or `PatientConsent` row); show badge on banner; case editor toggle; optional intake acknowledgment reuse of `confirmedAccurate` pattern |
| P1-3 | **DNR / advance directives** | P0 | M | Emergency-ready clinical chart | Add `code_status` enum (`Full code`, `DNR`, `DNI`, `Other`) + free-text advance-directive note; banner chip (high visibility); case editor + Overview edit |
| P1-4 | **Lung sounds** documentation | P0 | M | Students already auscultate in sim | Structured exam block: locations (e.g. RUL/RML/RLL/LUL/LLL) + finding (clear / crackles / wheeze / diminished / other) + free text; store as dedicated model or typed vitals/exam rows; show on Overview + pull into Objective/SOAP helper |
| P1-5 | Vitals path **smoke-check** for sim roles | P1 | S | She questioned updateability; code says Present | Confirm sim nurse/student can add BP during activity; fix permission gaps if any; document in instructor help blurb |
| P1-6 | Appointments **create/update** (if needed for case setup) | P2 | M | Display-only today | POST/PATCH appointments for instructor/case author; keep student read as today unless sim needs booking |

### Phase 1 acceptance

- [ ] Opening a sim patient shows photo, red allergies, emergency contact, code status, HIPAA badge
- [ ] Student/sim role can record BP and lung sounds during a visit
- [ ] Case author can set EC, HIPAA, code status, baseline lung/vitals for SPs
- [ ] No regression to SOAP, meds, labs, room placement

### Suggested order inside Phase 1

1. P1-1 (quick win, existing data)  
2. P1-3 + P1-2 (banner clinical identity)  
3. P1-4 (new sim documentation)  
4. P1-5 (verify)  
5. P1-6 (only if instructors ask)

---

## Phase 2 — Clinical pharmacy depth

**Goal:** Strengthen medication/clinical teaching inside the existing EHR — not a retail rebuild.

### Backlog

| ID | Item | Priority | Effort | Why | Implementation sketch |
|---|---|---|---|---|---|
| P2-1 | **Compounded medication** support | P0 | M | Explicit clinical example (celiac / commercial capsules) | Extend `Medication` (or child `CompoundRecipe`): `is_compound`, ingredients[], vehicle/base, allergen-avoidance notes, “why compounded”; UI toggle on Medications tab; seed 1–2 compound examples |
| P2-2 | **Verification queue** (clinical / fill check-off) | P0 | L | Core “tech/student enters → pharmacist verifies” teaching pattern | New `PrescriptionOrder` or extend med lifecycle: `draft → pending_verify → verified → released/held`; pharmacist role/station action; audit events; reuse patterns from `MedicationAdministration.review_*` and sim pharmacist station |
| P2-3 | SIG display helper | P1 | S | She spoke in SIG language (`1 PO QD`) | Derived or editable SIG string from dose + route + frequency; show on meds table and future labels |
| P2-4 | ICD-10 ↔ insurance **teaching callout** | P2 | S | Educational link she explained | On note/encounter with diagnoses, short UI note: “ICD-10 codes support billing/coverage decisions” + show linked payer fields already on patient — no real claim submission |
| P2-5 | Light clinical UX polish around new Phase 2 flows | P2 | S | Keep verify/compounds discoverable without a redesign | Small entry-point/copy tweaks only inside current shell (meds tab, sim pharmacist station) — no PioneerRx-style reshape |

### Phase 2 acceptance

- [x] At least one seeded compound med with rationale visible
- [x] Student can submit a med change/order; pharmacist/instructor can verify or hold with comment
- [x] SIG readable on medication list
- [x] Red allergies + interactions remain obvious during verify

### Suggested order inside Phase 2

1. P2-3 (cheap language win)  
2. P2-1 (compound model)  
3. P2-2 (verification — largest piece)  
4. P2-5 (small polish around verification)  
5. P2-4 (optional education)

---

## Phase 3 — Pharmacy operations simulation (Deferred stretch)

**Status: Deferred.** Not part of the committed roadmap. Only pick up if there is spare time and it can sit beside the current clinical chart without changing Margie’s product.

### Backlog (stretch only)

| ID | Item | Priority | Effort | Why | Implementation sketch |
|---|---|---|---|---|---|
| P3-1 | Simulated **claim / PBM** step | P0 | L | Process qty + SIG through insurance → reject/pay → pharmacist check | `ClaimSimulation`: medication, qty, days supply, SIG, payer, status (`paid`/`rejected`/`prior_auth`); scripted reject reasons for teaching; no real PBM |
| P3-2 | **Medication appearance** images | P0 | M | Pharmacist visual check | `MedicationProduct` (name, manufacturer, NDC stub, imprint, image URL/upload); link from verified fill; start with small curated set |
| P3-3 | **Barcode / scan simulation** | P1 | L | Fill workflow she described | Software scan: enter/scan code → resolve product → attach to fill; hardware not required |
| P3-4 | Controlled-substance **double-count** step | P1 | S | Part of her verify story | On C-II (flagged) fills, require second count confirmation before release |
| P3-5 | **Rx label + leaflet** preview | P0 | M | Affix label + “Walgreens bag leaflet” teaching artifact | On-screen/PDF preview: patient, drug, SIG, refills, mock pharmacy header, HIPAA/disposal boilerplate |

### Thin vertical slice (if ever doing a demo)

Order: **P3-5 → P3-2 → mini verify** (skip full PBM/barcode unless time remains).

---

## Out of scope / explicit non-goals (for now)

- Re-asking Margie to redefine the product setting  
- Rebuilding / reshaping the app into PioneerRx or retail pharmacy software  
- Real insurance / PBM connectivity  
- Real HIPAA legal compliance product (simulated teaching fields only)  
- Mandatory barcode hardware procurement  
- Specialty prior-auth engines beyond a stub status  
- Changing SOAP / destroying existing clinical overview to chase retail UI  

---

## Recommended roadmap (calendar-agnostic)

```text
Phase 0  ── SKIPPED (direction already set with Margie)
Phase 1  ── sim-lab chart gaps (EC, HIPAA, DNR, lung sounds)
Phase 2  ── compounds + verify workflow + SIG
Phase 3  ── DEFERRED stretch (claims / images / scan / labels)
```

**Ship cadence suggestion:** one phase ≈ one PR series (or sprint). Prefer Phase 1 fully done before Phase 2 verification work, so sim lab can use the chart immediately.

---

## Prioritized backlog (flat, for tracking)

Use this as the working queue. Status: `Todo` | `Doing` | `Done` | `Blocked` | `Deferred` | `Cancelled`.

| Order | ID | Title | Phase | Priority | Effort | Status |
|---|---|---|---|---|---|---|
| — | P0-1 | Confirm target setting with Margie | 0 | — | S | Cancelled |
| — | P0-2 | Confirm realism depth / Phase 3 gate | 0 | — | S | Cancelled |
| — | P0-3 | PioneerRx + clinical pharmacy pattern notes | 0 | — | S | Cancelled |
| — | P0-4 | Finalize Phase 3 In/Out/Demo-only | 0 | — | S | Cancelled |
| 1 | P1-1 | Emergency contact on banner/overview/case editor | 1 | P0 | S | Done |
| 2 | P1-3 | Code status / DNR / advance directives | 1 | P0 | M | Done |
| 3 | P1-2 | Simulated HIPAA / consent on file | 1 | P0 | M | Done |
| 4 | P1-4 | Lung sounds documentation | 1 | P0 | M | Done |
| 5 | P1-5 | Vitals entry path smoke-check for sim roles | 1 | P1 | S | Done |
| 6 | P1-6 | Appointments create/update for case setup | 1 | P2 | M | Todo |
| 7 | P2-3 | SIG display helper on medications | 2 | P1 | S | Done |
| 8 | P2-1 | Compounded medications | 2 | P0 | M | Done |
| 9 | P2-2 | Pharmacist verification / release workflow | 2 | P0 | L | Done |
| 10 | P2-5 | Light UX polish around Phase 2 flows | 2 | P2 | S | Done |
| 11 | P2-4 | ICD-10 billing teaching callout | 2 | P2 | S | Done |
| 12 | P3-5 | Rx label + leaflet preview | 3 | P0 | M | Deferred |
| 13 | P3-2 | Medication appearance images | 3 | P0 | M | Deferred |
| 14 | P3-1 | Simulated claim / PBM processing | 3 | P0 | L | Deferred |
| 15 | P3-3 | Barcode / scan simulation | 3 | P1 | L | Deferred |
| 16 | P3-4 | Controlled-substance double-count | 3 | P1 | S | Deferred |

---

## Engineering conventions (when implementation starts)

- One Alembic revision per meaningful schema slice (Phase 1 consents/code status; Phase 1 lung sounds; Phase 2 compounds; Phase 2 orders/verify; Phase 3 products/claims).
- Reuse `require` / `require_course` / audit `log_event` patterns; new pharmacist verify actions need permissions + denied audits.
- Seed via idempotent `_ensure_*` helpers; include at least one SP chart that exercises new Phase 1 fields.
- Frontend: banner + Overview first (high visibility for demos), then case editor parity so instructors can author SPs.
- Tests: happy path + one 403 per new mutating endpoint.

---

## Next action

**Phases 1–2 committed work is done** (P1-1–P1-5, P2-1–P2-5). Remaining optional: **P1-6** appointments write API; Phase 3 stretch (labels/claims/barcode) stays Deferred.
