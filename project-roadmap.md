# Doctor Diagnosis Assistant — Full Project Roadmap

A single reference covering everything from idea to deployment: architecture, data, models, form fields, compliance, and future additions. Built as a student project, starting with synthetic/public data, with doctor friends helping validate along the way.

**Core principle to hold onto throughout:** this is a *decision support tool*. It suggests, explains, and flags — the doctor always makes the final call. Every screen, output, and doc should reflect that.

---

## 0. Project Phases (the big picture)

| Phase | What happens | Data used |
|---|---|---|
| Phase 1 — Build & prototype | Build the full app, form, classifier, LLM reasoning layer | Public datasets + synthetic patients |
| Phase 2 — Doctor validation | Doctor friends test with realistic fake cases, give feedback | Synthetic, doctor-crafted cases |
| Phase 3 — Real pilot (future) | A real hospital/clinic tries it with real patients | Real patient data — **this is the trigger point for full DPDP compliance** (see Section 9) |

You are currently in **Phase 1**. Don't let Phase 3 concerns block Phase 1 work — but build habits now (Section 9.1) that make Phase 3 easier later.

---

## 1. System Architecture

```
Doctor (browser)
   │
   ▼
Frontend — intake form + results view
   │
   ▼
Backend API — auth, validation, storage, orchestration
   │
   ├──▶ Local Classifier (scikit-learn) ── fast structured prediction
   │
   └──▶ LLM Reasoning Layer (Gemini free tier) ── differential diagnosis + reasoning
   │
   ▼
Combined results shown to doctor (classifier prediction + LLM reasoning, side by side)
   │
   ▼
Doctor reviews, edits, confirms → logged as feedback
   │
   ▼
Database — patients, visits, diagnoses, audit log
```

**Why two prediction paths instead of one:**
- The **classifier** gives a fast, free, offline, quantifiable baseline prediction — good for testing at scale and cross-checking.
- The **LLM** gives the actual explainable output a doctor needs — reasoning, red flags, next steps — which a classifier alone can't produce.
- Both run every time; they're not alternatives, they're complementary layers.

---

## 2. Data — What to Use and Where to Get It

### 2.1 Datasets for the classifier (symptom → disease)

Use these instead of anything outcome-specific like heart-attack-only datasets — you want broad symptom-to-diagnosis mapping, not a single-condition risk score.

| Dataset | Size | Good for |
|---|---|---|
| Disease Prediction Using Machine Learning (Kaggle) | 132 symptoms → 42 diseases | First working pipeline — small, well-documented, lots of reference notebooks |
| Diseases and Symptoms Dataset (Kaggle) | 773 diseases, 377 symptoms, 246K rows | Scaling up once the basic pipeline works — much broader coverage |
| Symptom2Disease (Kaggle) | Natural-language symptom descriptions → disease | If you want the form/engine to also accept free-text symptom input |
| Synthetic Medical Symptom Dataset (Kaggle) | 5,000 rows, 8 conditions, severity scores | Very early sanity testing before committing to bigger datasets |

**Suggested order:** start small (132-symptom or synthetic 8-disease set) → get the pipeline working end to end → move to the 773-disease dataset for real coverage.

### 2.2 Synthetic patient data (for testing the whole app, not just the classifier)

- Ask your doctor friends to help create realistic fabricated patient cases — plausible symptom clusters, vitals ranges, and correct differential logic for each case. This is where their expertise adds the most value.
- Look into **Synthea** — an open-source synthetic patient generator built specifically for health IT testing without real-PHI risk. Worth exploring if hand-crafting cases doesn't scale.
- Keep a clear separation in your own repo/docs between "public dataset used for classifier training" and "synthetic cases used for end-to-end app testing" — they serve different purposes.

### 2.3 Rule checklist before using any dataset
- Confirm the license (Kaggle datasets are often CC0/public domain, but check each one)
- Confirm it's de-identified/synthetic, not scraped real patient records
- Note the source in your project docs (good practice, and useful if this gets evaluated academically)

---

## 3. The Classifier (Path A)

- **Tooling:** scikit-learn (free, local, no API needed)
- **Approach:** logistic regression or random forest as a first pass; both are simple, interpretable, and enough for a student project baseline
- **Handle carefully:**
  - Categorical columns need encoding (one-hot or similar)
  - Class imbalance — some diseases will have far fewer samples than others; use class weighting or resampling so the model doesn't just default to the most common label
  - Train/test split + basic metrics (accuracy, precision/recall per class — accuracy alone is misleading with imbalance)
- **Output:** a predicted disease label (+ ideally a confidence score) — feed this into the LLM layer as extra context if useful

---

## 4. The LLM Reasoning Layer (Path B)

### 4.1 Free API options (no budget needed)
| Provider | Notes |
|---|---|
| Google Gemini API | Free tier, no credit card, generous context window — best default choice |
| Groq | Free tier, very fast responses, runs open models like Llama 3.3 |
| OpenRouter | Aggregates multiple free models behind one API key — good for experimenting |

**Caveat to keep in mind:** free tiers are generally trained on submitted prompts — keep this layer on synthetic/test data only during Phase 1 and 2, never real patient data, until you've reviewed the provider's data policy properly.

### 4.2 What to send the LLM
- All structured intake fields (Section 6), cleanly formatted
- Optionally, the classifier's prediction as a hint/cross-check, not as ground truth

### 4.3 What to ask it to return
- Ranked differential diagnosis (top 3–5)
- Reasoning per item — which symptoms/vitals support or argue against it
- Red flags — anything urgent, surfaced first
- Suggested next steps — tests to order, referral needed
- Explicit instruction: state uncertainty, avoid false precision, never present a single definitive diagnosis

### 4.4 Prompt design tips
- Be explicit about output structure (ask for consistent formatting so your frontend can parse it reliably)
- Instruct it to reason step by step (differential-diagnosis style) rather than jumping straight to an answer
- Test the same case multiple times to see how consistent the reasoning is — inconsistency is useful signal for your doctor friends to review

---

## 5. Frontend — Doctor Intake Form (full field list)

Group into sections; use dropdowns/autocomplete over free text wherever possible so both the classifier and LLM get clean structured input.

### 5.1 Patient Demographics
- Full name, DOB/age, sex, gender identity (optional), weight, height (auto-BMI), occupation, contact info, patient ID/MRN

### 5.2 Visit Info
- Date/time, visit type (new/follow-up/emergency/telehealth), attending doctor, referring doctor

### 5.3 Chief Complaint
- Free text (short), duration, severity (1–10), progression (improving/worsening/stable)

### 5.4 History of Present Illness (OPQRST/SOCRATES framework)
- Onset, location (body map optional), duration, character, aggravating/relieving factors, radiation, associated symptoms (multi-select), timing pattern

### 5.5 Symptom Checklist
- Searchable multi-select, ideally mapped to a standard ontology (SNOMED CT / ICD-10) — present/absent/unsure, severity, duration per symptom

### 5.6 Vitals
- Temperature, BP, heart rate, respiratory rate, SpO2, blood glucose, pain score

### 5.7 Past Medical History
- Chronic conditions, past surgeries, hospitalizations, immunizations, family history

### 5.8 Medications & Allergies
- Current medications (name/dose/frequency), drug allergies + reaction type, other allergies

### 5.9 Social/Lifestyle History
- Smoking, alcohol, recreational drug use, diet, exercise, occupational exposure, travel history, sexual history (only if clinically relevant)

### 5.10 Physical Examination Findings
- Per-system structured input (cardiovascular, respiratory, abdominal, neuro, musculoskeletal, dermatological, ENT)

### 5.11 Investigations/Labs (optional at intake)
- Blood tests, imaging (with file upload), ECG, other tests

### 5.12 Doctor's Working Notes
- Free-text clinical impressions, kept separate from structured fields

---

## 6. Output Screen — What the Doctor Sees

- Classifier's quick prediction (baseline)
- LLM's ranked differential with reasoning
- Red flags, clearly highlighted
- Suggested next steps/tests
- Accept / edit / reject controls — doctor's final decision gets logged (useful feedback data for later improvement)

---

## 7. Backend & Database

### 7.1 Suggested stack
- Backend: Node.js (Express/NestJS) or Python (FastAPI — nice if you expand the ML side later)
- Database: PostgreSQL
- File storage: any S3-compatible storage for lab reports/images

### 7.2 Core tables
- `patients`, `visits`, `symptoms`, `vitals`, `medical_history`, `medications`, `allergies`, `lab_results`, `diagnoses` (engine output + doctor's final call), `audit_log`, `users`

### 7.3 Auth
- Role-based access (doctor/admin/nurse/read-only)
- Even in Phase 1 with fake data, build proper login — good habit, and needed for Phase 3 anyway

---

## 8. Build Order (MVP sequence)

1. Set up auth + basic account system
2. Build the structured intake form (Sections 5.1–5.9 first; exam/labs can come later)
3. Store patient/visit data in the DB
4. Build and train the classifier on a starter dataset (Section 3)
5. Wire up the LLM reasoning layer (Section 4)
6. Build the combined results screen
7. Add the doctor feedback loop (accept/edit/reject, logged)
8. Add labs/imaging upload
9. Test extensively with doctor-crafted synthetic cases
10. (Later, only when moving toward real deployment) — compliance work from Section 9

---

## 9. Compliance & Legal — India (DPDP Act)

### 9.1 Current phase (synthetic data only)
- DPDP does **not** apply yet — synthetic/fabricated data isn't personal data, so there's no legal obligation right now.
- Still worth building good habits early since retrofitting later is harder:
  - Design the schema so deleting a patient's data is actually possible
  - Include a `consent_given` field on patient records now, even if always `true`
  - Avoid hardcoding "store everything forever" logic
  - Get in the habit of only sending the LLM what's clinically necessary, not full record dumps

### 9.2 The trigger point
The moment **one real patient's data** enters the system (Phase 3), DPDP applies in full. Before that phase starts, you need:
- **Consent flow** — specific, informed, revocable consent notice before collecting any real patient data
- **Data Principal rights** — ability for a patient to know what's held, request correction/erasure
- **Security safeguards** — encryption at rest/in transit, RBAC, secure hosting (legally required, not optional — largest penalty category in the Act)
- **Breach notification readiness** — 72-hour reporting window to the Data Protection Board once aware of a breach; if CERT-In applicable, a stricter 6-hour window
- **Retention policy** — explicit, purpose-limited data retention with erasure once purpose is served
- **Cross-border data transfer check** — if using a non-India-hosted LLM API with real patient data, check current rules on transferring personal data outside India before sending real data to it
- **Legal sign-off** — talk to an actual India-based data-privacy lawyer before real patient data touches the system; this doc is a starting map, not legal clearance

---

## 10. Security Essentials (build in from the start, cost nothing to do early)

- Role-based access control
- Hashed/secure auth (MFA once you're past prototype stage)
- Encrypted storage even for test data (good habit)
- Session timeout
- Basic rate limiting on the API
- Audit logging: who accessed/edited what, when

---

## 11. Things That Can Be Added Later (nice-to-haves / stretch goals)

- **Body map UI** for symptom location selection (visual, faster than dropdowns)
- **Voice input** for doctors to dictate notes/symptoms instead of typing
- **Multi-language support** for both the form and LLM output
- **Trend view** — track a returning patient's vitals/symptoms over multiple visits
- **Specialist referral suggestions** based on the differential (e.g. "consider cardiology referral")
- **Drug interaction checker** — cross-reference suggested treatments against the patient's current medications/allergies
- **Explainability visualizations** — show which specific symptoms most influenced the classifier's prediction (e.g. via SHAP values)
- **Feedback-driven improvement loop** — use doctor accept/edit/reject data over time to fine-tune the classifier or refine LLM prompts
- **Offline/low-connectivity mode** — relevant for rural clinics, could lean more on the local classifier when the LLM API is unreachable
- **Confidence calibration testing** — systematically check whether the tool's "high/moderate/low" confidence labels actually match real-world accuracy on your test cases
- **Integration with lab equipment/EHR systems** — further down the line, if this moves toward real hospital adoption

---

## 12. Open Questions to Keep Revisiting

- Will the classifier and LLM outputs ever meaningfully disagree in testing — and if so, how should the doctor-facing UI communicate that?
- Which specialty/scope are you targeting first — general medicine, or something narrower to start?
- At what point (if any) do you want to move from Phase 1/2 toward an actual hospital pilot, and which hospital/doctor connection would that go through?
- Do you want free-text symptom entry (needs an NLP/LLM parsing step) in addition to structured checkboxes, or structured-only for now?
