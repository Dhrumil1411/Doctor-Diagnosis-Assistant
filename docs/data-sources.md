# Data Sources

Provenance and license record for every dataset used (roadmap §2.3 rule). `Data/` is gitignored — originals stay local; cleaned derivatives in `ml/artifacts/` are committed and regenerable.

## 1. Disease Prediction Using Machine Learning (Kaggle) — classifier training

- **Local path**: `Data/Kaggle/disease-prediction-42/` (`Training.csv` 4,920 rows, `Testing.csv` 42 rows)
- **Upstream**: Kaggle "Disease Prediction Using Machine Learning" — itachi9604 upload (131 binary symptom columns, 41 disease classes after audit; see `docs/dataset-notes.md`)
- **License**: CC0 1.0 Universal (Public Domain Dedication) — free to use, copy, modify, and distribute without restriction
- **Purpose**: Train/evaluate the symptom→disease logistic regression classifier only
- **Audit + cleaning**: See `docs/dataset-notes.md` — deduplication of `fluid_overload`, label-whitespace normalisation, phantom trailing column removed

## 2. Diseases and Symptoms Dataset (Kaggle)

- **Local path**: `Data/Kaggle/diseases-symptoms-773/diseases-symptoms-773.csv` (~246.9K rows, ~377 symptoms, first column `diseases`)
- **Upstream**: Kaggle "Diseases and Symptoms Dataset" — large multi-label diseases/symptoms mapping
- **License**: CC0 1.0 Universal (Public Domain Dedication) — free to use without restriction
- **Purpose**: Post-MVP scale-up candidate (not used in the MVP pipeline)
- **Known caveat**: Symptom vocabulary differs substantially from dataset #1; a mapping table will be required before any scale-up

## 3. Synthea Synthetic Patient Sample

- **Local path**: `Data/Synthea/*.csv` (full export: patients, encounters, conditions, observations, medications, allergies, procedures, immunizations, etc.)
- **Generator**: Open-source Synthea™ (synthetichealth/synthea) — produces realistic but entirely **synthetic** patient data; no real PHI
- **License**: Synthea generator: Apache License 2.0. Synthea-generated output is also Apache 2.0 licensed — free to use, modify, and distribute
- **Purpose**: End-to-end app testing only (Step 12 case generation). **Never** used for classifier training
- **SNOMED CT note**: SNOMED CT-coded conditions/observations do not map to binary symptom vectors; not classifier-compatible by design

## Privacy & Compliance Notes (India DPDP Act 2023)

The MVP operates exclusively with **synthetic and publicly-licensed data**. No real patient data is collected or processed during development or testing.

| Requirement | Status |
|---|---|
| Consent mechanism | ✅ Role-based access control gates all patient record writes; audit log captures every mutation |
| Data minimisation | ✅ Only clinically necessary fields collected (see spec §2) |
| Anonymisation | ✅ All test data is Synthea synthetic — zero real PHI |
| Access control | ✅ JWT + RBAC (Doctor / Admin / Nurse / Read-Only); admin-only audit log endpoint |
| Audit trail | ✅ `audit_log` table records actor, action, entity, timestamp, and IP for every mutation |
| Right to erasure | ⚠️ Not yet implemented (post-MVP backlog); database records are soft-deletable by design via `is_active` flag on users |
| Data residency | ⚠️ LLM inference calls data to Groq (US) / OpenRouter (US) — acceptable for a synthetic-data dev project; production use would require Indian data residency or on-prem LLM |

> **Note for production deployment**: Before handling real patient data, conduct a DPDP Data Protection Impact Assessment (DPIA), implement explicit consent screens, enable on-prem or India-resident LLM inference, and add a patient data-deletion workflow.
