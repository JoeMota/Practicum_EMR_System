# Simulation Center Feedback Summary

**Source:** Conversation transcript `Sun_Bowl_Dr_eng.txt` (Sun Bowl Dr. / Simulation Center)  
**Context:** Feedback from a Simulation Center employee on the pharmacy student EMR, with an eye toward sim-lab use cases and alignment with Margie Padiya (pharmacy school chair).  
**Goal of this doc:** Capture her suggestions and ideas as an implementation outline — not yet a build plan with tasks.

---

## 1. Conversation context

The system is currently an EHR-style app (office visit, demographics, allergies, vitals, labs, SOAP, appointments, teacher/class/patient assignment). The employee framed feedback around:

1. What **pharmacy setting** the product is meant to train for
2. What students already do in the **sim lab**
3. What would make the product feel more like real pharmacy / clinical pharmacy workflows

She noted the product feels more hospital / clinic / clinical-pharmacy oriented than retail claim-processing, and that clarifying the target setting with Margie should drive almost all design choices.

---

## 2. Strategic / process suggestions

### 2.1 Confirm the target setting with Margie

**Ask explicitly:** *What setting are you trying to target for simulated patients / this demographic of students?*

**Possible answers she listed:**

| Setting | Notes from conversation |
|---|---|
| Hospital | Inpatient / institutional workflows |
| Community / retail | PioneerRx-style; claims, filling, verification |
| Clinical pharmacy | Likely intended target — optimize drugs from EMR data; act more like providers |
| Specialty pharmacy | Complex meds, prior auth, etc. |
| Ambulatory | Possible, less emphasized |
| LTC | Mentioned; she doubts this is the focus |

**Her read:** It sounds like **clinical pharmacy** — students optimizing medications based on EMR findings, making independent decisions, counseling patients in care-center style visits (similar to community clinic pharmacist visits).

### 2.2 Use real pharmacy software as a reference

- Look at **PioneerRx** (community pharmacy) to see how techs/pharmacists use systems day-to-day.
- Across CVS, Walgreens, independents, and hospitals, pharmacy systems share a common processing + verification pattern — the current product is not that pattern yet.
- Prompt / compare the product against **clinical pharmacy** systems and fold those improvements in.

### 2.3 Align with existing sim-lab activities

Students already:

- Talk to simulated patients (SPs)
- Obtain BP and allergy background
- Counsel patients
- Check lung sounds (full exam)
- Document SOAP notes
- Use testing/SP rooms; 3–5 larger labs as holding rooms

The EMR should support those activities directly (vitals entry, lung sounds, counseling/SOAP, patient identity context).

---

## 3. Feature suggestions (her wishlist)

Suggestions below are grouped by theme. Items she explicitly recommended are marked as **Suggested**. Things she praised as already good are marked **Keep / affirm**.

### 3.1 Patient identity & administrative

| Item | Type | Detail |
|---|---|---|
| Patient photo | **Suggested** | Wanted a photo of the patient on the chart |
| Emergency contact | **Suggested** | Per patient |
| Simulated HIPAA agreement | **Suggested** | Simulated consent / HIPAA on file |
| DNR / advance directives | **Suggested** | Especially if trending clinical / emergency-ready chart content |
| Demographics, insurance, overview | **Keep / affirm** | Overview (office visit, demographics, allergies, vitals, labs) matches what pharmacists in that setting review |

### 3.2 Clinical documentation & assessment

| Item | Type | Detail |
|---|---|---|
| Allergies shown in red | **Keep / affirm** | Explicitly liked the red allergy treatment |
| Editable / updatable vitals (e.g. BP) | **Suggested** | Current values alone are not enough — students take BP and need to record/change values (chart/history) |
| Lung sounds documentation | **Suggested** | Students perform lung sounds in sim; add a place to record findings (and optionally codes / descriptors for advantageous sounds) |
| SOAP notes | **Keep / affirm** | Margie wanted SOAP; employees see that as correct for satellite / hospital / clinical training |
| Appointments | **Keep / affirm** | Fits care-center / clinical visit workflows |
| ICD-10 encounter coding | **Suggested (educational)** | Example: general encounter coded as E11.65; teach that ICD-10 drives insurance payment |

### 3.3 Medications & pharmacy workflow

| Item | Type | Detail |
|---|---|---|
| Medication library | Existing | Confirm completeness; she asked how many meds / whether a library exists |
| Compounded medications | **Suggested** | Support compounds (e.g. celiac patient cannot take commercial capsules — need compound without problematic fillers) |
| Med details: dose, SIG, frequency, adherence, cost/access, indication | **Keep / affirm** | Adding meds with how taken, frequency, adherence, access/cost, indication, active/inactive — matches pharmacy practice |
| Simulated insurance / PBM claim processing | **Suggested** | Simulate processing claims for a patient: medication, tablet count, SIG (e.g. `1 PO QD`), through PBM/insurance, then pharmacist check-off |
| Pharmacist verification step | **Suggested** | Tech (or student) enters/fills; pharmacist must verify before release — core real-world pattern |
| Medication appearance photos (by manufacturer) | **Suggested** | Upload / show what the pill looks like per manufacturer (as real pharmacy systems do after scan) |
| Barcode scan workflow | **Suggested** | Receive Rx → type → grab stock bottle → scan → count → pharmacist scans → pill image + imprint → controlled substance double-count → release |
| Rx label + patient leaflet | **Suggested** | Generate (optionally print) bottle label and leaflet (drug info, HIPAA/privacy text, refill count, disposal guidance — the “stuff you throw away” at Walgreens) |

### 3.4 Product direction / UX research

| Item | Type | Detail |
|---|---|---|
| Curtail UI to chosen setting | **Suggested** | Once setting is known, reshape screens to match that pharmacy type |
| Compare vs clinical pharmacy products | **Suggested** | Ask “what would a clinical pharmacy system do better?” and implement a version of those gaps |

---

## 4. Suggestion outline (implementation-oriented grouping)

Pure outline of what implementing her ideas would mean, without committing to order or scope yet:

### A. Clarification dependency (before deep pharmacy UX)

1. Confirm target setting with Margie (hospital / community-retail / clinical / specialty / ambulatory / LTC)
2. Use that answer to decide whether to lean EHR-clinical vs fill/verify/claims

### B. Sim-lab alignment (high relevance regardless of setting)

1. Patient photo on chart
2. Emergency contact
3. Simulated HIPAA agreement
4. DNR / advance directive fields
5. Reliable vitals entry + history (especially BP update after measurement)
6. Lung sounds documentation fields
7. Preserve SOAP, appointments, red allergies

### C. Clinical / medication depth

1. Expand medication model for compounds
2. Keep/enhance indication, adherence, access/cost, active status
3. Educational ICD-10 coding tied to encounters / billing narrative

### D. Pharmacy operations simulation (more community/retail; still useful teaching)

1. Simulated claim / PBM processing (SIG, quantity, insurance path)
2. Verification queue (submit → pharmacist verify → release)
3. Medication image library by NDC/manufacturer
4. Barcode scan simulation (hardware optional; software scan/lookup is the core)
5. Label + leaflet generation (print optional; PDF/preview sufficient)

### E. Reference & design research

1. Review PioneerRx (and similar) for community patterns
2. Benchmark against clinical pharmacy EMR/workflow expectations
3. Optionally map rooms/holding areas to sim-lab logistics if room assignment remains part of student use

---

## 5. What she already likes (do not break)

- Overall EHR overview for clinical-style review
- Allergy highlighting in red
- Ability to add medications with frequency, adherence, access/cost, indication, active/inactive
- SOAP support
- Appointments
- Labs / results entry direction
- General polish / AI-assisted build quality (positive reaction to the product)

---

## 6. Open questions she left with us

Resolved for planning purposes: stay on the **current clinical EMR** Margie already iterated on; do not re-ask setting or reshape toward PioneerRx. Retail realism items (claims/barcode/labels) remain optional stretch only. Compounded meds stay in Phase 2 of the implementation plan.

---

## 7. Next step (per user plan)

1. ~~Summarize and outline suggestions~~ ← this document  
2. ~~Turn this outline into an implementation plan (prioritized backlog / phasing)~~ → [sim-center-implementation-plan.md](./sim-center-implementation-plan.md)  
3. Implement Phase 1 (starting with emergency contact surfacing); Phase 0 skipped
