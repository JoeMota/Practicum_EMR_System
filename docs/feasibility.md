# Feasibility assessment: patient portal, billing, and insurance

**Assessment basis:** repository inspection and `Resources/emr_implementation_checklist_and_customer_answers.md`. Portal hardening below has been implemented on the feature branch; no unrelated application files were changed.

## Summary

- **Patient portal:** The API and patient-facing page exist. Successful chart reads now write `portal.view` audit events, labs are sorted newest first with a stable name tie-break, and portal API tests cover access, isolation, auditing, hidden fields, and read-only behavior. Visit metadata may still not match the signed note summary.
- **Billing:** Current scope is educational ICD-10/CPT code selection with no prices. CPT 99441–99443 are present but the AMA deleted them effective 2025; they must be treated as stale entries pending the customer's catalog decision. Actual patient balances, statements, estimates, and payments were not found.
- **Coding data gaps:** CPT selections are code/label only, with no diagnosis link. The shared answer key has no expected CPT field. A JSONB shape change can add the first link without a database migration; adding a new answer-key column requires one.
- **Insurance:** Patient records store payer/member/group identifiers; no insurer workflow is implemented. This assessment excludes external connections.

## Nine hypotheses

| # | Hypothesis | Result | Evidence (`file:line`) |
|---|---|---|---|
| 1 | A patient portal API is registered. | **Confirmed** | `backend/app/main.py:7,32`; `backend/app/api/routes/portal.py:11,14`. |
| 2 | The portal provides labs, last visit, prescribed medication, and active medication list, with labs sorted newest first. | **Confirmed** | `backend/app/api/routes/portal.py:48-75`; tests `backend/tests/test_portal.py:14-49`; UI `frontend/src/features/portal/PatientPortalPage.tsx:32-53`. |
| 3 | Patient access is bound to the logged-in account’s linked chart. | **Confirmed** | `backend/app/api/routes/portal.py:21-25`; actual patient portal route `frontend/src/App.tsx:57`. |
| 4 | Portal access is server-side read-only. | **Confirmed** | GET-only handler and permission check: `backend/app/api/routes/portal.py:14-22`; patient role grants `portal:view`: `backend/app/services/access.py:40`. |
| 5 | Successful portal chart views are audit-logged. | **Confirmed** | `backend/app/api/routes/portal.py:78-89` writes and commits `portal.view`; `backend/tests/test_portal.py:14-49` asserts the event. |
| 6 | Portal-specific automated tests exist. | **Confirmed** | `backend/tests/test_portal.py:14-91` covers portal data, chart isolation, unlinked accounts, role denial, auditing, hidden fields, sorting, and write-method rejection. |
| 7 | CPT 99441, 99442, and 99443 are in the selectable list. | **Confirmed** | Present but obsolete: `backend/app/clinical_sections.py:59-61`. AMA says these codes were deleted effective January 2025; audio-only E/M codes were introduced in 98008–98015, and 98016 is a brief communication service. The app should not add replacements without the customer's decision. [AMA overview](https://www.ama-assn.org/practice-management/cpt/how-ama-meets-need-new-telehealth-cpt-codes). |
| 8 | Patient-facing balances, statements, estimates, or payments are implemented. | **Refuted** | Note stores CPT codes in JSON only: `backend/app/models/clinical.py:176`; configured CPT list has no amounts: `backend/app/clinical_sections.py:39-61`. |
| 9 | The insurance fields implement eligibility, claims, or authorization workflows. | **Refuted** | Only payer/member/group fields exist: `backend/app/models/clinical.py:72-74`; no insurance workflow route/service found. |

## Effort and files by feature

Effort is relative engineering size for this repo, assuming the educational use case and no external payer connectivity.

| Feature | Effort | Likely files touched | Alembic migration? |
|---|---:|---|---|
| Portal audit event, stable lab ordering, and portal tests | **S (implemented)** | `backend/app/api/routes/portal.py`; `backend/tests/test_portal.py` | **No**; uses existing audit table and portal data model. |
| Link each selected CPT code to one or more diagnoses | **M** | `backend/app/schemas/clinical.py` (`IcdCode`, `NoteOut`, `DraftPatch`, `InstructorEdit`); `backend/app/models/clinical.py` only if JSON defaults/typing are adjusted; `backend/app/services/notes.py`; `frontend/src/types/index.ts`, `frontend/src/api/notes.ts`, `frontend/src/features/encounters/NoteEditorPage.tsx`; note tests | **No** if each CPT selection stores its diagnosis code(s) inside the existing `ClinicalNote.cpt_codes` JSONB column (`backend/app/models/clinical.py:176`). Existing JSON rows need backward-compatible defaults; no relational column is required. |
| Add expected CPT selections to each shared case answer key | **M** | `backend/app/models/clinical.py` (`CaseAnswerKey`); `backend/app/schemas/clinical.py` (`AnswerKeyIn/Out`); `backend/app/services/answer_keys.py`; `backend/app/services/hidden.py` (both snake_case and camelCase); case answer-key editor/grader UI; `backend/tests/test_sprint3.py` for grader visibility and student non-disclosure | **Yes**: add an `expected_cpt_codes` JSONB column to `case_answer_keys`, with an empty-list default for existing cases. |
| Confirm/update the educational CPT catalog and test its allowed contents | **S** | `backend/app/clinical_sections.py`, `backend/app/services/reference_data.py`, `frontend/src/features/encounters/NoteEditorPage.tsx`, `backend/tests/test_client_answers.py` | **No**; the catalog is code, and note selections are already stored as JSONB. Do not add replacement codes until the customer decides the teaching catalog. |
| Patient statements, estimates, balances, or payments | **L** | New billing model/schema/route/service; Alembic revision; portal billing UI and API client; tests | **Yes** for persisted billing records. Not in the current customer answer; confirm scope first. |
| **Insurance option 1:** instructor-written scenario context on a case, using existing payer/member/group fields | **S** | `backend/app/schemas/clinical.py` (`CaseIn`); case create/update serialization in `backend/app/services/cases.py`; `frontend/src/features/cases/CaseEditorPage.tsx` and related case types; case tests | **No** if encoded in the existing columns (`backend/app/models/clinical.py:72-74`). `CaseIn` and the editor do not expose them now, so API/UI wiring is required; a separate free-text narrative column would need a migration. |
| **Insurance option 2:** persisted mock payer scenarios and outcomes for teaching | **M** | New scenario/outcome models and schemas, routes/services, instructor/student UI and API clients, seed data, tests; likely `backend/app/main.py` for the new router | **Yes** for persisted scenario/outcome tables. This keeps the existing M estimate and does not connect to external insurers. |
| Frontend test runner and first portal/coding/answer-key UI tests | **M** | `frontend/package.json`, `frontend/package-lock.json`, test configuration, new `frontend/src/**/*.test.tsx` files | **No**. |

### CPT-to-diagnosis and answer-key details

`IcdCode` contains only `code` and `label`, and note response/input schemas type `cpt_codes` as `list[IcdCode]` (`backend/app/schemas/clinical.py:193-195,233,256,501`). To associate a CPT choice with diagnoses, define a CPT-specific selection schema containing `code`, `label`, and one or more diagnosis codes, then update note create/read/patch, instructor edit, API client types, editor UI, and validation/tests. The underlying `ClinicalNote.cpt_codes` column is JSONB (`backend/app/models/clinical.py:176`), so changing the JSON document shape does **not** require an Alembic schema migration. Existing rows need a tolerant parser/default for absent diagnosis links; a data backfill is optional if historical links cannot be inferred.

`CaseAnswerKey` currently stores only diagnoses, plan points, and rationale (`backend/app/models/clinical.py:224-233`; `AnswerKeyIn`/`AnswerKeyOut` start at `backend/app/schemas/clinical.py:405,411`). Adding expected CPT codes requires new schema fields plus a new JSONB database column and Alembic migration. Add `expected_cpt_codes` and `expectedCptCodes` to `backend/app/services/hidden.py` so neither form leaks in student-visible payloads (`backend/app/services/hidden.py:8-13`). Extend the answer-key tests to prove graders can read/edit the expected codes and students cannot see either spelling; existing answer-key tests begin at `backend/tests/test_sprint3.py:235`.

## Audit and test findings

- **Portal views are audit-logged after successful response construction.** `portal.view` records actor, patient, course, and request IP (`backend/app/api/routes/portal.py:78-89`). Failed and denied requests do not receive this success event.
- **Portal labs are sorted** newest collection date first, then name ascending for equal dates (`backend/app/api/routes/portal.py:49-50`).
- **Portal tests now exist** in `backend/tests/test_portal.py`; they cover chart data, cross-patient isolation, unlinked accounts, student/instructor denial, absence of denied-view events, hidden keys, read-only methods, sort order, and successful audit fields.
- **Frontend tests:** `frontend/package.json:6-11` has build/lint/dev/preview scripts but no test script, and no frontend test/spec files were found. Adding a test runner is worthwhile before expanding role-sensitive portal, coding, and answer-key flows; start with portal access/display, CPT-diagnosis association, and hidden expected-CPT checks. It is not a prerequisite for the already-working production build.

## Cross-cutting

### Permissions

Keep backend and frontend permission definitions aligned. Any new role capability for patient billing or mock insurance scenario access must update both `backend/app/services/access.py` and `frontend/src/utils/permissions.ts` (current patient permission examples: `access.py:40`, `permissions.ts:47`). Route guards must still enforce authorization on the backend; hiding a UI route alone is insufficient. CPT-to-diagnosis links and expected CPT answer-key fields can use the existing note and case-author/grader permissions, so they do not inherently need new permission strings.

### Audit events

- Add `log_event` for successful portal reads.
- Student draft saves are not audit-logged: `save_draft` changes fields and flushes without `log_event` (`backend/app/services/notes.py:74-95`), and `PATCH /notes/{note_id}` calls it without an audit event (`backend/app/api/routes/notes.py:164`). Audited note actions include creation, signing, co-signing, return, comments, addenda, instructor edits, and scoring (`backend/app/services/notes.py:62-297`). Auditing signed submissions is probably sufficient for this training app; do not add draft-save auditing.
- Expected CPT answer-key read/update uses the existing answer-key route audit events (`backend/app/api/routes/cases.py:164-192`); preserve these when adding the field.
- If patient balances/payments are later approved, log charge/adjustment, statement, payment/refund, and status changes. For mock insurer exercises, log scenario submission, outcome, grading, and instructor configuration changes if retained for assessment.

### Alembic migrations

- CPT-to-diagnosis association in the existing note JSONB: **none**.
- Portal read auditing using the current audit-events table: **none**.
- Expected CPT codes on `CaseAnswerKey`: **one migration** adding a JSONB column with an empty-list default.
- Patient balances/statements/payments: **additional migration(s)** for persistent billing records, if approved.
- Persisted mock insurance scenarios/outcomes: **additional migration(s)**, if approved. Static fixtures alone need none.

## Baseline commands and results

| Command | Result |
|---|---|
| Python 3.11 venv, `pip install -r backend/requirements.txt`, Postgres via `docker compose up -d`, then `pytest -q` | **Local backend runs are blocked on this Windows host.** Python 3.11 venv creation succeeded under Temp, but the exact requirements install failed at pinned `uvloop` (`uvloop does not support Windows`); Docker and WSL are unavailable, so PostgreSQL could not start. Direct `pytest -q` also fails immediately: `'pytest' is not recognized as an internal or external command`. GitHub Actions runs the backend suite against PostgreSQL 16 on pull requests (`.github/workflows/ci.yml:12-36`). |
| Node 22, `npm ci && npm run build` | **Passed in a temporary copy of frontend** to keep the repo unchanged. Used official Node v22.22.0; the downloaded ZIP SHA-256 matched Node's published checksum. `npm ci` added 226 packages and reported 16 audit advisories (12 moderate, 4 high). `npm run build` succeeded; Vite warned that the generated JS chunk exceeds 500 kB. |

## Open questions for the customer

1. Is billing still code selection only with no prices, or are patient balances/statements/estimates/payments now required?
2. Is "incident-to billing" just context for the code-selection exercise, or must students apply incident-to supervision requirements? The implementation should not infer those rules.
3. For the CPT catalog decision: 99441-99443 remain in the app but AMA deleted them effective 2025. Should they remain for historical exercises or be removed, and which current catalog should instructors use? Should each selected CPT link to exactly one diagnosis or allow multiple diagnoses? Should answer keys include expected CPT codes and acceptable alternatives? No replacement codes are added by this assessment. [AMA CPT telehealth changes](https://www.ama-assn.org/practice-management/cpt/how-ama-meets-need-new-telehealth-cpt-codes).
4. Which insurance approach is wanted: short instructor-written case context using the existing payer/member/group fields (Option 1), or persisted mock payer scenarios and outcomes (Option 2)?
5. Should the visit date/type come from the same signed note whose summary is displayed? Current endpoint takes date/type from `patient.encounter` and summary from the latest signed/cosigned note (`backend/app/api/routes/portal.py:28-38,67-70`).
