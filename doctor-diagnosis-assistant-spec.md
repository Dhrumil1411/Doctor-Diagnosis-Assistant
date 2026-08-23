# Doctor Diagnosis Assistant — Project Specification

A clinical decision support (CDS) web app where a doctor enters patient details and receives a ranked list of likely diagnoses with reasoning and suggested next steps.

**Important framing:** this tool must be built and marketed as *decision support*, not a diagnostic authority. The doctor always makes the final call. Keep this in every screen, every output, and every doc.

---

## 1. System Overview

```
Doctor (browser)
   │
   ▼
Frontend (intake form + results view)
   │
   ▼
Backend API (auth, validation, storage)
   │
   ▼
Diagnosis Engine (LLM or rules engine)
   │
   ▼
Database (patients, visits, diagnoses, audit log)
```

---

## 2. Doctor-Side Intake Form — Full Field List

This is the core data-entry UI. Group it into sections; use dropdowns/autocomplete wherever possible instead of free text, so the diagnosis engine gets structured input.

### 2.1 Patient Demographics
- Full name
- Date of birth / age
- Sex (biological, relevant for diagnosis)
- Gender identity (optional, separate field)
- Weight, height (auto-calc BMI)
- Occupation (relevant for some conditions — e.g. exposure history)
- Contact info
- Patient ID / MRN (medical record number)

### 2.2 Visit / Encounter Info
- Date & time of visit
- Visit type (new patient, follow-up, emergency, telehealth)
- Attending doctor
- Referring doctor (if any)

### 2.3 Chief Complaint
- Free text (short) — "what brought the patient in today"
- Duration (onset: hours/days/weeks/months)
- Severity (mild/moderate/severe or 1–10 scale)
- Progression (improving, worsening, stable, fluctuating)

### 2.4 History of Present Illness (HPI)
Structured using the classic **OPQRST / SOCRATES** framework:
- Onset (sudden vs gradual)
- Location (body region, with option to click on a body map)
- Duration
- Character (sharp, dull, burning, cramping, etc.)
- Aggravating factors
- Relieving factors
- Radiation (does it spread anywhere)
- Associated symptoms (multi-select checklist — fever, nausea, fatigue, weight loss, etc.)
- Timing (constant, intermittent, time of day pattern)

### 2.5 Symptom Checklist (multi-select, searchable)
- Autocomplete search over a standard symptom ontology (ideally mapped to **SNOMED CT** or **ICD-10** codes) so symptoms are structured, not free text
- Each symptom should let the doctor set: present/absent/unsure, severity, duration

### 2.6 Vitals
- Temperature
- Blood pressure (systolic/diastolic)
- Heart rate
- Respiratory rate
- SpO2 (oxygen saturation)
- Blood glucose (if relevant)
- Pain score

### 2.7 Past Medical History
- Chronic conditions (diabetes, hypertension, asthma, etc.) — multi-select
- Past surgeries
- Past hospitalizations
- Immunization history
- Family history (conditions in first-degree relatives)

### 2.8 Medications & Allergies
- Current medications (name, dose, frequency)
- Known drug allergies + reaction type
- Other allergies (food, environmental)

### 2.9 Social / Lifestyle History
- Smoking status (current/former/never, pack-years)
- Alcohol use
- Recreational drug use
- Diet
- Exercise
- Living situation / occupation exposure risk
- Travel history (important for infectious disease differentials)
- Sexual history (only if clinically relevant to the case)

### 2.10 Physical Examination Findings
- General appearance
- System-wise exam findings (cardiovascular, respiratory, abdominal, neuro, musculoskeletal, dermatological, ENT, etc.) — structured per-system input, not one big text box

### 2.11 Investigations / Lab Results (optional at intake, can be added later)
- Blood tests (CBC, LFT, KFT, etc.)
- Imaging (X-ray, CT, MRI, ultrasound) — file upload + report text
- ECG
- Other specialty-specific tests
- Ability to upload PDF/image reports

### 2.12 Doctor's Working Notes
- Free-text clinical notes / impressions (kept separate from structured data — useful for the LLM as extra context, and for the doctor's own record)

---

## 3. Output — What the Diagnosis Engine Should Return

- **Ranked differential diagnosis list** (top 3–5 likely conditions)
- For each: a confidence indicator (e.g. "high/moderate/low likelihood" — avoid fake-precise percentages)
- **Reasoning**: which symptoms/vitals/labs support or argue against each diagnosis
- **Red flags**: anything urgent/emergency that needs immediate attention
- **Suggested next steps**: tests to order, specialist referral if needed
- Doctor can accept, edit, reject, or add their own diagnosis — this feedback should be logged (useful for improving the system later)

---

## 4. Diagnosis Engine — Approaches

| Approach | Description | Notes |
|---|---|---|
| Rule-based | Hand-coded decision trees / Bayesian symptom-disease mapping | Transparent but slow to build, limited coverage |
| ML model | Trained on labeled clinical datasets | Needs real medical data + ML expertise |
| LLM-assisted | Structured patient data fed into an LLM with a clinical-reasoning prompt | Fastest to build for MVP; must show reasoning, not just an answer |

**MVP recommendation:** LLM-assisted approach — send structured intake data to an LLM with a prompt that asks it to reason step by step (differential diagnosis style) and cite which findings support each possibility.

Prompt design should include:
- All structured fields from the intake form, cleanly formatted
- Explicit instruction to output a ranked differential with reasoning per item and flag emergencies first
- Instruction to state uncertainty and recommend confirmatory tests rather than a single definitive diagnosis

---

## 5. Tech Stack (suggested default)

- **Frontend**: React / Next.js, form library (React Hook Form), body-map / autocomplete components
- **Backend**: Node.js (Express/NestJS) or Python (FastAPI — good if you later add real ML models)
- **Database**: PostgreSQL (structured, relational — good fit for patient/visit/diagnosis data)
- **File storage**: S3-compatible storage for lab reports/images
- **Diagnosis engine**: LLM API to start; can add a custom-trained model later
- **Auth**: Role-based access control (doctor, admin, nurse, read-only), MFA
- **Hosting**: AWS/GCP/Azure with a HIPAA-compliant (or regionally equivalent) configuration

---

## 6. Core Database Tables (rough schema)

- `patients` — demographics
- `visits` — one row per encounter, links to patient
- `symptoms` — coded symptom entries per visit
- `vitals` — per visit
- `medical_history` — chronic conditions, surgeries, family history
- `medications` — current meds per patient
- `allergies`
- `lab_results` — with file attachments
- `diagnoses` — engine output + doctor's final decision, per visit
- `audit_log` — every access/edit, who/when/what (required for compliance)
- `users` — doctors/staff with roles

---

## 7. Compliance & Legal (do this early, not last)

- Depending on your country, a diagnosis-suggesting tool may be classified as a **medical device / clinical decision support software** — check local regulatory requirements (FDA in the US, CDSCO in India, MDR in the EU) before launch.
- **Data privacy law compliance**: HIPAA (US), DPDP Act (India), GDPR (EU) — whichever applies to your users.
- Encryption at rest and in transit.
- Full audit logging of who accessed/edited what.
- Clear disclaimers on every diagnosis output: "decision support only, not a substitute for clinical judgment."
- Data retention & deletion policy.
- Informed consent flow if patient data is being processed by a third-party AI API.

---

## 8. Security Essentials

- Role-based access control
- MFA for doctor/admin accounts
- Encrypted database + encrypted file storage
- Session timeout / auto-logout
- Rate limiting & abuse monitoring on the API
- Regular security audits if handling real patient data

---

## 9. Suggested MVP Build Order

1. Auth + doctor account system
2. Structured patient intake form (sections 2.1–2.9 first; exam/labs can come later)
3. Store patient/visit data in DB
4. Wire up diagnosis engine (LLM-assisted) with a well-tested prompt
5. Results screen: ranked differentials + reasoning + red flags
6. Doctor feedback loop (accept/edit/reject diagnosis — logged)
7. Add labs/imaging upload
8. Add audit logging + compliance basics
9. Pilot with a small group of real doctors before wider rollout

---

## 10. Open Questions to Settle Before Building

- Which country/region will this launch in first? (Determines which regulations apply.)
- Will you handle real patient data from day one, or start with de-identified/synthetic data for testing?
- Solo specialty (e.g. general medicine) or multi-specialty from the start?
- Will doctors input data themselves, or will there be intake staff/nurses doing data entry?
