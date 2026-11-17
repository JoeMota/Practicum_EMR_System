# Sprint 3 Plan

Historical snapshot. Later sprints added Roomed, real vitals points, section comments, activity sessions, and server-side 800-number checks. Do not treat the status table below as the current code.

Source: `Practicum_EMR_Requirements_v2.docx` (Oct 6, 2026). Code checked at `origin/master` f7870a7 (PR 20); the local `feature/postgres-backend` tree is identical to it. Plan only; no code was changed.

Scope rule: only items the doc puts in "Sprint 3 scope" are planned (CASE-01, CASE-02, CASE-03, CASE-05, NFR-15, REV-01, REV-03, DOC-01, DOC-02, DOC-06, CHART-04, CHART-05, TRK-01, TRK-02, ADM-04), plus the NFRs the doc attaches to every Must (NFR-14, NFR-17, NFR-18). Open, Could, Should-not-in-sprint and Deferred items are listed only where the code status needed checking.

---

## Part 1. Real status of every Unverified or Partial item

| ID | Doc status | Real status | Evidence |
|---|---|---|---|
| ADM-03 | Shipped; verify 800-number | **Shipped (client-validated only)** | `RosterRowIn.university_id` in `backend/app/schemas/clinical.py:258-262`; stored on `User.university_id` (`backend/app/models/user.py:54`); regex `^800\d{6}$` enforced in `frontend/src/features/admin/parseRoster.ts:32`. The server (`backend/app/api/routes/courses.py:96-165`) validates the UTEP email only, never the 800 format. |
| ADM-04 | Partial (remove only) | **Partial, confirmed** | `DELETE /courses/{id}/roster/{user_id}` hard-deletes the `CourseMembership` row (`courses.py:168-195`). No deactivate/reactivate. `User.is_active` (`user.py:57`) is account-wide, not per course. Patients and notes are not deleted, but the student can no longer reach them because `require_course` (`backend/app/services/access.py:72-77`) finds no membership. Re-import re-adds the membership (`courses.py:135-153`). |
| ADM-07 | Unverified | **Missing** | Templates are hard-coded in `frontend/src/features/encounters/noteTemplates.ts`; the backend stores `template_id` as a `Literal["pharmacy_mtm","pt_daily_soap","general_soap"]` string (`schemas/clinical.py:12`). No templates table, no admin or course-level management. |
| CASE-02 | Partial (snapshot exists for reset) | **Partial, but for a different reason** | `assign_case` (`backend/app/services/charts.py:232-333`) deep-copies the source into a new `Patient` row with its own allergies, meds, problems, labs, vitals, encounter and appointments, so copies are already independent of the source. `Patient.snapshot` (`models/clinical.py:70`) is populated only for practice charts and used only by `reset_practice`. There is no case-edit endpoint at all, so "editing never changes copies" is untested rather than protected. |
| CHART-01 | Partial (search fields unverified) | **Partial** | MRN is unique (`models/clinical.py:41`). Clone MRNs come from `_unique_mrn` (`charts.py:367-375`): `TR-{10000+row_count+offset}-{initials}`, derived from a table count, so "sequential" is approximate; seed MRNs are hand-written (`TR-20001`, `TR-M-STARK`). Search is a client-side filter over first name, last name, MRN and owner name (`frontend/src/features/patients/PatientListPage.tsx:39-46`). No DOB search; no server-side search endpoint. |
| CHART-03 | Partial | **Partial, confirmed** | `frontend/src/features/patients/PatientChartPage.tsx:20-26` has five top pill-tabs (Overview, Notes, Medications, Labs, Appointments & Referrals). No left column; Vitals, Allergies and Problems live inside Overview (`components/SummaryTab.tsx`). |
| CHART-04 | Partial (chart of stored values) | **Partial, and the doc overstates it** | `Vital` stores only `label` and `value` (`models/clinical.py:125-130`), no timestamp. `VitalsChart.tsx:33-41` (`trend()`) fabricates every point except the last from a hash seed, and `labelsFor()` (lines 44-59) fabricates the dates. Only the current value is real. Pain exists only by convention as a vital with label `Pain` (seed: Marcus, Sofia, Linh). |
| CHART-06 | Partial | **Partial, confirmed** | `Medication` has name, dose, route, frequency, indication, adherence (`models/clinical.py:92-101`). The MTM note has a med-rec table with Continue/Modify/Discontinue/Hold plus comment (`frontend/src/features/encounters/components/MedRecTable.tsx`). No "how taken" or "access or cost" fields. |
| CHART-07 | Unverified | **Partial** | `Allergy` has substance, reaction, severity (`models/clinical.py:83-89`). No type column. Seed contains food (Shellfish) and environmental (Cats, Latex) items but they are untyped. |
| DOC-01 | Unverified | **Partial** | All three templates have S, O, A, P sections (pharmacy adds MR) with labeled fields; `NoteFields.tsx:22-49` renders them as a vertical stack with S/O/A/P badges. Structured fields beyond free text are only the ICD-10 picker and the med-rec table. `content` is a flat `dict[str, str]` (`schemas/clinical.py:191, 212`). The backend knows nothing about sections or required fields; `missingRequired` is client-only (`noteTemplates.ts:161-169`). |
| DOC-03 | Unverified | **Missing** | OLDCARTS appears only as placeholder text in the general SOAP HPI field (`noteTemplates.ts:112`). No prompts, no SCHOLAR-MAC option. |
| DOC-07 | Unverified | **Missing** | Plan sections are free-text fields (`noteTemplates.ts:56-63, 93-98, 129-133`). The general template labels one field "Plan by problem" but nothing organizes it per problem. |
| DOC-09 | Unverified | **Shipped (frontend-defined)** | `pharmacy_mtm` "Comprehensive medication review (MTM)" and `pt_daily_soap` "PT daily note (SOAP)" in `noteTemplates.ts:27-101`; `defaultTemplateFor` picks by discipline (lines 155-159); backend accepts both ids. |
| DOC-11 | Shipped; verify roomed | **Partial; no "Roomed"** | `ENCOUNTER_STATUS` in `charts.py:16` is `Scheduled, Checked in, In progress, Checked out, Closed`; same list in `frontend/.../StatusDialog.tsx:6` and `SummaryTab.tsx:14`. Seed also writes `"Waiting"` (`seed.py:755, 912`), which is not in the allowed set. |
| REV-03 | Unverified (return exists; comments unclear) | **Partial** | `NoteComment` has note, author, body, kind, created_at (`models/clinical.py:167-176`); no section anchor. Comments are created only inside `cosign_note` and `return_note` (`services/notes.py:144-152, 175`), so they are whole-note. No standalone comment endpoint. The "instructor cannot change the student's text" half is enforced: `save_draft` requires `note.author_id == author.id` (`notes.py:71-72`). Frontend type already allows `kind: "comment"` (`frontend/src/types/index.ts:136`) but the backend never emits it. |
| TRK-01 | Partial (audit log only) | **Partial, confirmed** | `AuditEvent` (`backend/app/models/audit.py`) records `chart.view`, `note.view`, `note.create`, `note.sign_submit`, `auth.login` etc. `GET /audit` (`routes/audit.py:15-47`) returns a flat per-course list, no per-student aggregation, no date range. `User.last_login_at` is set at login (`routes/auth.py:54`) but is global, not per course. No sessions or active time anywhere; `rg heartbeat|visibilitychange frontend/src` finds nothing. |

## Part 2. Where the doc and the code disagree (flagged, not resolved)

1. **CHART-04**: the doc calls the vitals chart "chart of stored values". It is a synthetic trend around one stored value (`VitalsChart.tsx:33-59`). Anything built on it (TRK or grading screenshots) should know this.
2. **DOC-11**: doc states are `scheduled, checked in, roomed, in progress, completed`; code states are `Scheduled, Checked in, In progress, Checked out, Closed`. "Roomed" and "completed" do not exist; "Checked out"/"Closed" do. Seed uses `"Waiting"`, which the API would reject on PATCH.
3. **CHART-04 "across all encounters"**: `Encounter.patient_id` is `unique` (`models/clinical.py:136`), so a chart has exactly one encounter. Multi-visit history is not possible with the current model and is not in the Sprint 3 list.
4. **SEC-04 "students see only their own activity"**: students get 403 on `GET /audit` (`routes/audit.py:24`; asserted in `tests/test_workflows.py:218-219`). They see nothing, not "their own".
5. **CASE-02**: protection comes from copy-on-assign, not from `Patient.snapshot`. The doc's parenthetical points at the wrong mechanism.
6. **CHART-01 "system-assigned, sequential"**: clone MRNs are count-based and race-prone (`charts.py:367-375`), seed MRNs are literals.
7. **REV-01/REV-02**: `NoteReviewPage.tsx:94-98` renders an "Open rubric (file.pdf)" button with no handler; `Course.rubric_file_name` is a string only. No file exists. Not in Sprint 3 (REV-02 is held on C3), but the dead button sits on the screen Step 3 modifies.
8. **ADM-03**: 800-number format is validated in the browser only.

---

## Part 3. Sprint 3 items, in the doc's order

Shared conventions for every step below:

- Role checks stay server-side via `require(role, permission)` / `require_course` / `ensure_visible` in `backend/app/services/access.py` and `charts.py`; the `role` query parameter pattern is unchanged. New permissions are added to `ROLE_PERMISSIONS` (`access.py:11-32`), `PERMISSIONS` in `seed.py:53-63`, and the frontend matrix in `frontend/src/utils/permissions.ts`.
- Every denied action logs an audit event with `result="denied"`, every mutation logs `result="ok"`, following `log_event` in `services/audit.py`.
- Per-student assessment copies stay private (`ensure_visible`, `charts.py:28-47`) and signed notes stay addendum-only (`save_draft` / `add_addendum`, `services/notes.py`).
- Seed stays idempotent: new rows go through `_ensure_*` lookups keyed on a natural key (MRN, email, body text), never unconditional inserts.
- One Alembic revision per step so steps can ship independently and the bottom of the list can be cut.
- NFR-18: each step's tests live in `backend/tests/test_workflows.py` (or a new `test_sprint3.py`) and include at least one 403 for every new endpoint.

### Step 1. Case authoring (CASE-01, CASE-02)

**Data model** (`backend/app/models/clinical.py`, Alembic revision `sprint3_01_cases`)

- Reuse `Patient` as the case master rather than adding a parallel table; `assign_case` already clones a `Patient` and `AssignCaseDialog` already groups sources by `case_template_id`. Add `mode="case"` to the allowed set (today: `practice`, `assessment`). A master has `owner_id=None`, is never listed to students, and is the clone source.
- Add `Patient.past_medical_history: Text default ""` (doc lists PMH; the model has surgical, family and social only). Problems list stays as the coded PMH.
- Add `Patient.created_by_id: FK users nullable` and keep `updated_at` from `TimestampMixin` so authorship shows on the case list.
- `assign_case` sets `clone.snapshot = chart_snapshot(source)` for assessment copies too (today only practice charts carry one). This is what the doc means by "each copy keeps its own snapshot"; copies remain independent rows as today. `reset_practice` keeps its `mode == "practice"` guard so assessment snapshots are inert.

**API** (new `backend/app/api/routes/cases.py`, registered in `main.py`)

- New permission `case:author` for `instructor` and `admin`.
- `GET /cases?course_id&role` list masters in the course (instructor/admin; students 403 + audit `case.list denied`).
- `POST /cases?course_id&role` blank-form create. Body `CaseIn`: demographics (first, last, preferred, dob, sex_at_birth, pronouns), chief_complaint, hpi, past_medical_history, surgical_history, family_history, social_history, encounter type, care_setting, lifecycle, plus child lists `allergies[]`, `medications[]`, `problems[]`, `labs[]`, `vitals[]` (baseline; see Step 5 for the attribution fields). MRN assigned by `_unique_mrn`-style helper with a `CASE-` prefix. `case_key = str(new uuid)`.
- `GET /cases/{id}?role`, `PATCH /cases/{id}?role` full-replace of scalar fields and child lists (same `_replace_children` approach as reset, `charts.py:157-173`). PATCH never touches rows where `source_patient_id == id` (CASE-02).
- `POST /patients` (assign) keeps its contract; `source` may now be a `case` master or a practice chart. Students still cannot call it (`patient:create`).
- Audit: `case.create`, `case.update`, `case.view` (instructor views are not audited today for masters; add for parity with `chart.view`).

**Frontend**

- `frontend/src/api/cases.ts`; routes `/cases`, `/cases/new`, `/cases/:caseId` for `instructor` and `admin` in `App.tsx`; SideNav item "Cases" for both roles.
- `features/cases/CaseListPage.tsx` (title, MRN, discipline hint, updated, "Assign" shortcut) and `CaseEditorPage.tsx` with sections mirroring the doc's list; child lists as small editable tables reusing `SummaryTab` column sets.
- `AssignCaseDialog.tsx`: source list comes from `GET /cases` plus practice charts, not from `templatesFrom(rows)`; `PatientListPage` must not count or show `mode === "case"` rows in either tab.

**Tests**

- Instructor `POST /cases` 200 and the row has `mode="case"`, `owner_id=None`; student `POST /cases` 403 with a `denied` audit row.
- `GET /patients?role=student` never lists the master; `GET /patients/{master}` as student is 403.
- Assign from master, then `PATCH /cases/{master}` to change chief complaint and a medication; re-read the copy: unchanged, and `copy.snapshot` equals the pre-edit master.
- Seed run twice produces one master per seeded case.

**Acceptance criteria**

- An instructor can create a case from an empty form with every field in CASE-01 and assign it to one or more students.
- Editing a master after assignment changes nothing on any student's copy.
- Students cannot see, open, or list masters.
- Reset of practice charts behaves exactly as before.

### Step 2. Answer key with server-side hiding (CASE-03, CASE-05, NFR-15)

Write the leak tests first (doc instruction), then the model.

**Data model** (revision `sprint3_02_answer_key`)

- New table `case_answer_keys`: `id`, `patient_id FK patients unique` (the master), `diagnoses JSONB` as an ordered list of `{rank, code, label, rationale}`, `plan_points JSONB list[str]`, `rationale Text`, `updated_by_id FK users`, timestamps.
- `Patient.answer_key_released_at: DateTime nullable` on assessment copies. Default null. No release endpoint or UI this sprint (REV-07 is Could); the column exists so the hiding rule has a single predicate.
- The key is read live from the copy's `source_patient_id` master at review time; it is not snapshotted into the copy. Flagged in Questions.

**API**

- `PUT /cases/{case_id}/answer-key?role` upsert, `case:author`.
- `GET /cases/{case_id}/answer-key?role` for masters and `GET /patients/{copy_id}/answer-key?role` for copies (resolves the master). Both require `case:author` or `note:cosign`; `student`, `front_desk`, `patient` get 403 regardless of `answer_key_released_at`, with an audit `answer_key.view denied`.
- Hiding rule, one place: `services/hidden.py` with `HIDDEN_FOR_STUDENTS = {"answer_key", "answerKey", "expected_diagnoses", "plan_points", "triggers", "rubric"}` and `assert_no_hidden(payload)` used by tests. `patient_out` and `note_out` never embed the key; the only path is the dedicated endpoint.

**Frontend**

- Answer key section on `CaseEditorPage`: ordered diagnoses with ICD-10 autocomplete from the curated subset in `features/encounters/icd10.ts` (16 codes today; doc asks for 30 to 50 from the client), move-up/move-down buttons (keyboard-reachable, NFR-16), rationale per diagnosis, plan points list, overall rationale.
- `api/cases.ts`: `getAnswerKey`, `putAnswerKey`.

**Tests**

- Leak walk: for every endpoint a student can call (`/patients`, `/patients/{id}`, `/patients/{id}/notes`, `/notes/{id}`, `/patients/{id}/appointments`, `/patients/{id}/referrals`, `/auth/me`), recursively assert no key in `HIDDEN_FOR_STUDENTS` appears anywhere in the JSON, including nested objects and lists, for a copy whose master has a key.
- Student `GET /patients/{copy}/answer-key` 403 and audited; instructor 200 with diagnoses in rank order; admin 200.
- Key upsert replaces, not appends; `PUT` by student 403.
- Setting `answer_key_released_at` directly in the DB still yields 403 for students this sprint (release is REV-07, not built).

**Acceptance criteria**

- An instructor can attach an ordered list of expected diagnoses with ICD-10 codes, plan points and rationale to a case.
- No student-role response from any endpoint contains answer-key data, and the test suite proves it.

### Step 3. Side-by-side review (REV-01, REV-03)

**Data model** (revision `sprint3_03_note_comments`)

- `NoteComment.section_id: String(10) nullable` (`S`, `O`, `MR`, `A`, `P`, or null for whole-note). Existing `returned`/`cosigned` rows stay null.
- `kind` gains `"comment"`; the frontend type already has it.
- No change to `ClinicalNote`; instructors remain unable to change `content` (`save_draft` author check stays and gets an explicit test).

**API**

- `POST /notes/{note_id}/comments?role` body `{section_id, body}`; `note:cosign`; allowed while `status == "pending_review"`; 409 otherwise; audit `note.comment`. Returns `NoteOut`.
- `note_out.feedback[]` adds `section_id`.
- `GET /patients/{copy_id}/answer-key` from Step 2 is what the review screen reads.

**Frontend**

- `NoteReviewPage.tsx`: three columns on `lg` (note | answer key | review actions), two on `md` (note | key, actions below). Answer key panel lists expected diagnoses in order, plan points, rationale; shows "No answer key for this case" for copies without a master (all pre-Sprint 3 seeded copies).
- `NoteFields.tsx`: optional `comments` and `onComment(sectionId)` props; a "Comment on this section" button in each section header for reviewers; existing comments shown under the header. `FeedbackThread.tsx` prefixes section label.
- `NoteEditorPage.tsx`: when `status === "returned"`, section comments render inside the matching section, not only in the top alert.
- Leave the FERPA alert and the inert "Open rubric" button alone (REV-02/REV-04 are held on C3); see Questions.

**Tests**

- Instructor posts a section comment: 200, `feedback` contains it with `section_id`, audit row exists.
- Student posts a comment on their own note: 403.
- Instructor `PATCH /notes/{id}` with content: 403 (existing behavior, now asserted).
- Comment on a `cosigned` note: 409.
- Student `GET /notes/{id}` sees the comments (they are feedback, not hidden content) and the leak walk from Step 2 still passes.

**Acceptance criteria**

- On the review screen the instructor sees the student's note and the case answer key at the same time without scrolling between them on a laptop width.
- Instructor feedback is attached to a specific S/O/A/P section and the student sees it in place when the note is returned.
- No instructor action changes the student's text.

### Step 4. Structured SOAP (DOC-01, DOC-02, DOC-06)

**Data model**

- No new tables. `ClinicalNote.content` and `diagnoses` are JSONB already.
- `IcdCode` schema gains `rationale: str | None` (`schemas/clinical.py:160-162`); list order is the priority order (DOC-06). Seed diagnoses without rationale stay valid.
- New `backend/app/services/templates.py`: server-side registry of template ids, section ids and the DOC-02 prefill map. The frontend `noteTemplates.ts` keeps labels and layout; the backend registry is the source of truth for section ids (needed by Step 3 comment validation) and prefill.

**API**

- `POST /patients/{id}/notes` (`create_draft`) prefills `content` from the chart per template: chief complaint into `reason` (pharmacy), `subjective` (PT), `cc` (general); demographics line ("57-year-old male") prepended to that field; vitals formatted as `label value` lines into `objective` (pharmacy), `measures` (PT), `exam` (general). Prefill uses the latest non-error entry per vital label from Step 5 (or current rows if Step 5 is cut). Prefill happens once at `version 1`; the chart is never written (NFR-14).
- `PATCH /notes/{id}` accepts `diagnoses[].rationale`; order preserved. 409 on stale version unchanged.
- `POST /notes/{id}/comments` validates `section_id` against the registry.

**Frontend**

- `NoteFields.tsx` ICD-10 field becomes an ordered problem list: pick adds to the end, move-up/move-down buttons, rationale textarea per problem, remove. Autocomplete limited to the curated subset.
- `missingRequired` (`noteTemplates.ts:161-169`): a problem without rationale blocks signing in assessment mode (interpretation of "writes a rationale per problem"; flagged in Questions).
- DOC-01: each S/O/A/P section already has labeled fields plus free text; the remaining work is to make section ids stable (`S`,`O`,`A`,`P`, pharmacy `MR`) and show the prefilled values as editable text with a one-line "Prefilled from the chart" hint.

**Tests**

- Create draft on Rosa (TR-20001): `content.reason` contains the chief complaint and the age/sex line; `content.objective` contains `146/88`.
- Chart unchanged after draft creation.
- Save diagnoses `[E11.65 (rationale A), I10 (rationale B)]`, reorder, re-read: order and rationale preserved.
- Stale `expected_version` still 409.

**Acceptance criteria**

- A new note opens with the encounter's chief complaint, vitals and demographics already in the right fields.
- Picking ICD-10 codes builds an ordered problem list the student can reorder, each with its own rationale.
- Draft, sign, review, return and addendum flows behave as before.

### Step 5. Vitals entry (CHART-04, CHART-05)

**Data model** (revision `sprint3_05_vitals_entries`)

- `Vital` gains `recorded_at DateTime(tz) server_default now()`, `recorded_by_id FK users nullable` (null = case baseline), `encounter_id FK encounters nullable`, `entered_in_error Boolean default false`, `error_reason Text nullable`, `error_marked_by_id FK users nullable`, `error_marked_at DateTime nullable`. `label` and `value` stay strings so existing parsing (`VitalsChart.tsx:61-71`) keeps working.
- Backfill: existing rows `recorded_at = encounter.date`, `recorded_by_id = NULL`.
- `chart_snapshot` / `_replace_children` (`charts.py:157-225`) carry the new fields so practice reset restores baseline entries exactly; student-recorded entries on practice charts are dropped on reset (flagged in Questions, since ARC-03 archives notes rather than deleting).
- `assign_case` copies baseline, non-error entries with `recorded_by_id=None`.
- No UPDATE or DELETE path for vitals anywhere.

**API**

- New permission `vitals:record` for `student`, `instructor`, `admin` pending the client's answer on who may author vitals (doc Question 9).
- `POST /patients/{id}/vitals?role` body `{entries: [{label, value}], recorded_at?}`; `ensure_visible` then `require(role, "vitals:record")`; attributes to the caller; `encounter_id = patient.encounter.id`; 409 on `mode == "case"` ("edit the case instead"). Audit `vitals.record`.
- `POST /patients/{id}/vitals/{vital_id}/entered-in-error?role` body `{reason}`; allowed for the entry's author or `note:cosign` holders; sets the error fields, never deletes. Audit `vitals.entered_in_error`.
- `patient_out.vitals[]` extends `VitalOut` with `id, recorded_at, recorded_by_name, entered_in_error, error_reason` (one path, NFR-13; no separate GET).

**Frontend**

- `features/patients/components/VitalsEntryDialog.tsx`: BP, Pulse, RR, Temp, SpO₂, Weight, Height, Pain 0-10, time (default now). Opened from the Vitals card on `SummaryTab`.
- `VitalsHistory.tsx`: table, one row per `recorded_at`, one column per label, attribution column, entered-in-error rows struck through with reason, "Mark entered in error" action with reason prompt.
- `VitalsChart.tsx`: delete `trend()`, `labelsFor()` and the time-range buttons; plot real points from entries (excluding errors) sorted by `recorded_at`; with one point show the value and "One reading on {date}".
- Caption on the card: "Baseline values come from the case. Entries you add are timestamped and attributed; nothing is overwritten." (NFR-14)

**Tests**

- Student records vitals on own copy: 200, `recorded_by_name` is the student, baseline rows untouched.
- Student records on another student's copy: 403 (existing `ensure_visible`), audited.
- `PUT`/`DELETE /patients/{id}/vitals/{vid}`: 405.
- Entered-in-error keeps the row, sets the flag and reason; a second call is 409.
- Reset restores baseline only; assign copies baseline only.
- Note prefill (Step 4) uses the latest non-error entry per label.

**Acceptance criteria**

- Authorized roles can add a vitals entry to an encounter; each entry shows who and when.
- Earlier entries are never changed; mistakes are visibly marked entered-in-error with a reason.
- The Vitals card shows a real history table and a trend of stored values including pain, with no synthetic points.

### Step 6. Activity report (TRK-01, TRK-02)

**Data model** (revision `sprint3_06_activity`)

- New table `activity_sessions`: `id`, `user_id FK users`, `course_id FK courses`, `role String(20)`, `started_at`, `last_seen_at`, `active_seconds Integer default 0`, `heartbeats Integer default 0`. Index on `(user_id, course_id, started_at)`.
- Counts come from `AuditEvent` by `actor_user_id`, `course_id`, `occurred_at` range: charts opened = `chart.view ok`, notes started = `note.create`, notes submitted = `note.sign_submit`. Last sign-in = `User.last_login_at` (global; `auth.login` audit rows carry no `course_id`, flagged in Questions).

**API**

- `POST /activity/heartbeat?role` body `{course_id}`; `require_course`; no audit row (would flood the log). Server rule: if a session for `(user, course)` has `last_seen_at` within 150 s, extend it and add `min(now - last_seen_at, 60)` seconds; otherwise open a new session. Ignore heartbeats less than 30 s apart. Returns 204.
- `GET /courses/{course_id}/activity?role&from&to` under `audit:view` (instructor/admin). Returns one row per enrolled student: `user_id, full_name, last_sign_in, sessions, active_seconds, charts_opened, notes_started, notes_submitted`, plus `measurement` text (NFR-17): "Active time counts minutes in which the tab was visible and the user clicked, typed or scrolled within the last 60 seconds. Background tabs and idle time are not counted." Students 403 + audit `activity.report denied`.

**Frontend**

- `features/activity/useHeartbeat.ts` mounted in `components/AppShell.tsx`: every 60 s, send a heartbeat only if `document.visibilityState === "visible"` and the last `pointerdown`/`keydown`/`scroll` was under 60 s ago. Stop on sign-out and on idle sign-out (existing `IDLE_MS` in `AuthContext.tsx:8`).
- `features/activity/ActivityReportPage.tsx` at `/reports/activity` for instructor/admin; SideNav "Activity report"; date range inputs defaulting to the last 14 days; table per student; the `measurement` sentence shown above the table.

**Tests**

- Two heartbeats 60 s apart (clock injected via a `now` dependency) yield one session with `active_seconds == 60`; a third after 10 minutes opens a second session.
- Heartbeat for a course the user is not in: 403.
- Report as instructor includes a seeded student with `charts_opened >= 1` from the seeded `chart.view` audit row (`seed.py:326`); as student: 403.
- Seed adds a few `activity_sessions` rows idempotently (lookup by `user_id + started_at`).

**Acceptance criteria**

- An instructor can pick a course and date range and see, per student, last sign-in, sessions, active time, charts opened, notes started and submitted.
- Active time only accrues while the tab is visible and the user is active, and the screen says so.

### Step 7. Roster lifecycle (ADM-04)

**Data model** (revision `sprint3_07_membership_status`)

- `CourseMembership.deactivated_at DateTime nullable`, `deactivated_by_id FK users nullable`. Active = null. No row deletion, no account change, no change to patients or notes.

**API**

- `POST /courses/{course_id}/roster/{user_id}/deactivate` and `.../reactivate` under `roster:import` (instructor of that course or admin, same `_staff_role` rule as today, `courses.py:198-204`). Audit `roster.deactivate`, `roster.reactivate`.
- `memberships_for` (`access.py:48-58`) excludes deactivated rows, so every course-scoped call by a deactivated student fails `require_course` with the existing 403; login still works; `user_out` omits the course from their picker.
- `_student_in_course` (`charts.py:354-364`) requires an active membership, so no new assignments go to inactive students.
- `GET /courses/{id}/roster` returns `RosterMemberOut(PublicUser)` with `roster_status: "active" | "inactive"` and `deactivated_at`. Instructors still see the student's existing copies and notes in the patient list.
- Roster import of a deactivated email reactivates instead of re-adding; `RosterImportResult` gains `reactivated: int`.
- Existing `DELETE .../roster/{user_id}` stays unchanged (flagged in Questions).

**Frontend**

- `RosterImportPage.tsx`: status chip per row; "Deactivate" / "Reactivate" buttons; "Remove" moves behind a confirmation that explains the difference. `AssignCaseDialog` filters to active students.

**Tests**

- Deactivate Daniel in PHAR 5320: his `GET /patients?course_id` is 403; his copies and notes still load for the instructor; `GET /auth/me` no longer lists the course.
- Reactivate: access restored with the same patient ids and notes.
- Student calls deactivate: 403 and audited.
- Import containing a deactivated student: `reactivated == 1`, `added == 0`.

**Acceptance criteria**

- An instructor can deactivate and later reactivate a student in a course; nothing about the student's account, charts or notes is deleted or re-entered.

---

## Part 4. Cross-cutting work

- **NFR-18**: add `npm run lint` to the frontend job in `.github/workflows/ci.yml` (today it runs `npm ci` and `npm run build` only). Each step above lists its 403 tests.
- **NFR-14**: enforced by Step 1 (`case:author` only on masters), Step 5 (append-only vitals), Step 4 (prefill reads, never writes).
- **NFR-15**: Step 2 `services/hidden.py` and the leak walk, extended as triggers/rubric arrive later.
- **NFR-17**: the `measurement` sentence returned by the report endpoint and shown on the page.
- **Migrations**: seven small revisions chained after `8d7590d48592`; each step independently revertible.
- **Seed**: two authored masters (one pharmacy, one PT) with answer keys and baseline vitals, a handful of student vitals entries, a few activity sessions, one deactivated membership for the demo. All via `_ensure_*` by natural key. Existing seeded assessment copies keep `source_patient_id=None` and therefore have no answer key; the review page shows the empty state for them.
- **Cut line**: the doc says cut from the bottom. Steps 1 to 3 are the minimum that answers the client's main ask; Steps 4 and 5 touch the same `Vital` rows and should ship together if either ships.

---

## Part 5. Questions before build

### For the client

These five are already in the doc's question list. Each entry gives what she said, what the code does today, and what changes depending on her answer. The first three gate Steps 2 to 4; the last two can be answered during the sprint.

**1. Is the answer key one per case, shared by every instructor, or can each instructor keep their own?**

- Where it came from: OURS 00:00:10 (item 2). She asked whether answers could be attached to a case so that "different instructors" do not grade differently and she can see the note "side to side". Her stated goal is less variance between graders.
- Code today: there is no answer key anywhere. A case exists as a `Patient` row; instructors are a per-course membership (`CourseMembership`), and PHAR 5320 already has two instructors in the seed (Gerardo and Joe), so the question is real for the demo data.
- If shared (plan assumption): one `case_answer_keys` row per master, `patient_id` unique. Any instructor in the course can edit it; the audit trail records who changed it. Simple model, matches her stated goal.
- If per instructor: the key becomes `(patient_id, instructor_id)` unique, the review screen must pick the key of the reviewing instructor (`routed_to_id` on the note), and a student's note can be graded against different keys depending on who they routed to. That reintroduces the variance she said she wants to remove, so we should confirm before building it.
- What to ask her: "If two instructors teach the same course, should they both see and edit the same answer key for a case?"

**2. When an instructor disagrees with a note, should they comment and return it, or edit the student's text?**

- Where it came from: OURS 00:02:11 (item 5, conflict C6). A teammate told her instructors "can edit whatever they need to, and then they will return it for revision." The code has never done that.
- Code today: co-sign locks the note; return hands editing back to the student; `save_draft` rejects any caller who is not the author (`services/notes.py:71-72`). Instructor input is a whole-note comment attached to the return or co-sign action. Every state change is audited with the actor, so authorship in the record is unambiguous.
- If comment-and-return (plan, Step 3): comments gain a section anchor so feedback lands next to the S, O, A or P block it concerns; the student's text is never touched by anyone else. This is what the S1 instructor answers describe and what keeps the audit trail meaningful.
- If edit at co-sign: we would need instructor edits stored as a separate layer (tracked changes) so the student's original survives, plus a UI to show both versions. That is a larger build than anything in Sprint 3 and conflicts with S1's complaint that EHR Go lets records be "freely changed."
- Also affected: the review page currently shows a FERPA notice ("grades aren't stored in the EMR") and an "Open rubric" button that does nothing because no rubric file exists. Both relate to C3 (rubric scoring). Her answer here and on C3 decides whether those stay, change, or go.
- What to ask her: "We told you instructors could edit the note at co-sign. The system actually lets instructors comment on specific sections and send the note back for the student to fix. Is that the behavior you want, or do you need instructors to change the text themselves?"

**3. Which ICD-10 codes do the first pharmacy and PT cases need?**

- Where it came from: T3 00:02:01 (item 24) and S1. Picking a code should add a problem to the assessment in order; the doc's Sprint 3 note says to use "a small curated ICD-10 subset, not the full code set."
- Code today: `frontend/src/features/encounters/icd10.ts` has 16 codes. The seeded charts use codes outside that list (for example I82.401, Z96.641, F03.918, I69.351, M75.101, S93.401A, G43.909), so a student cannot currently pick several of the diagnoses already on the chart.
- Why it gates Steps 2 and 4: the answer key (Step 2) and the student's problem list (Step 4) both pick from this list. If the key contains a code the student cannot select, the side-by-side comparison is unfair to the student.
- What we need: 30 to 50 codes, grouped by discipline, including the hidden diagnoses she intends to plant in the first assessment cases (her UTI, hypertension, diabetes example from T3 00:00:33 implies N39.0, I10 and E11.x at minimum). If she cannot produce a list quickly, we can propose one assembled from the codes already in the seed and the two course topics (pharmacotherapy skills, PT clinical practice) and have her approve it.
- What to ask her: "Can you give us the 30 to 50 diagnosis codes you expect students to use in the first pharmacy and PT cases, or would you rather approve a draft list from us?"

**4. Who may record vitals during a simulated visit: any clinical student, or only a nursing or MA role?**

- Where it came from: T2 00:01:15 (item 17) describes a nurse or MA entering vitals and pushing them into the note; T3 00:03:05 (item 25) asks whether prefilled vitals can be edited and where the vitals section is; conflict C2.
- Code today: vitals are read-only values seeded on the chart. The roles are `student`, `instructor`, `admin`, `front_desk`, `patient`; disciplines include nursing, but a nursing student holds the same `student` role as a pharmacy student. There is no MA role or discipline.
- Plan assumption (Step 5): a new `vitals:record` permission granted to student, instructor and admin, so any student can add a timestamped entry on a chart they can already open. Baseline vitals authored by the instructor are never overwritten; mistakes are marked entered-in-error.
- If she wants nursing or MA only: the check becomes permission plus discipline (`CourseMembership.discipline_id`), and pharmacy or PT students would see the vitals history but not the entry button. That also means a pharmacy-only course has nobody who can add vitals unless the instructor does it. Worth confirming she accepts that consequence.
- What to ask her: "In a pharmacy or PT course with no nursing students, who enters vitals during the visit: the student working the case, or only you as instructor?"

**5. What does a struggling student look like in numbers?**

- Where it came from: OURS 00:00:10 (item 3). She said students who "haven't even visited the website for that long" tend to do worse and successful students "have more time in there." She also mentioned per-student reports and possibly at-risk alerts (item 4).
- Code today: the audit log records chart views and note actions with timestamps but nothing about time on site; the instructor dashboard shows review-queue counts and flagged labs, not student activity. Her expectation is ahead of the code.
- Plan (Step 6): the report will show last sign-in, sessions, active time, charts opened, notes started and notes submitted per student over a date range. Active time comes from a heartbeat sent only while the tab is visible and the user is interacting, and the screen states that definition so idle tabs are not read as study time (NFR-17).
- Why we ask: the report can be built without her answer, but the default date range, sort order and any threshold highlighting (TRK-03, Should, not this sprint) depend on which number she actually looks at. If she thinks in "days since last sign-in," the default sort is by last sign-in; if she thinks in "hours per week," the default is active time over the last seven days.
- What to ask her: "When you say a student hasn't been in the system enough, what number would you look at first: days since they last signed in, total active time this week, or cases they have not started by the due date?"

### For the team

Decisions the doc does not settle:

6. Should the answer key be read live from the master at review time (plan) or frozen into the copy's snapshot at assign time (CASE-02 reading)? Live means a typo fix reaches graders; frozen means the key cannot drift after assignment.
7. DOC-06: should a missing per-problem rationale block signing in assessment mode? The plan says yes.
8. Practice reset deletes student-recorded vitals entries (snapshot restore). Acceptable, or should they be archived like notes (ARC-03)?
9. ADM-04: keep the existing hard-delete "Remove" alongside deactivate/reactivate, or retire it? The plan keeps it unchanged.
10. DOC-11: rename encounter states to the doc's list (adding "Roomed", replacing "Checked out"/"Closed" with "Completed") in this sprint, or leave as is and correct the doc? Either way the seed's `"Waiting"` values need to match the allowed set.
11. CHART-04 "across all encounters": with `Encounter` 1:1 per chart, Sprint 3 delivers history within the single encounter. Is that acceptable for this term, or does the model need multiple encounters per chart (not in the doc's Sprint 3 list)?
12. TRK-01 "last sign-in": per course would need `course_id` on `auth.login` audit rows, which login does not know. Use the global `User.last_login_at` (plan) or record the first heartbeat of a session as the per-course sign-in?
13. SEC-04 says students see only their own activity; the code gives them 403. Should Step 6 add a student-facing "my activity" view, or correct the doc?
