# Data Sources

Provenance and license record for every dataset used (roadmap §2.3 rule). `Data/` is gitignored — originals stay local; cleaned derivatives in `ml/artifacts/` are committed and regenerable.

## 1. Disease Prediction Using Machine Learning (Kaggle) — classifier training

- Local: `Data/Kaggle/disease-prediction-42/` (`Training.csv` 4,920 rows, `Testing.csv` 42 rows)
- Upstream: Kaggle "Disease Prediction Using Machine Learning" (Training/Testing file pair matches the itachi9604 upload) → confirm against your Kaggle download history
- License: TODO(user) — open the dataset page on Kaggle and record the exact license here
- Purpose: train/evaluate the symptom→disease classifier only
- Audit + cleaning: see `docs/dataset-notes.md`

## 2. Diseases and Symptoms Dataset (Kaggle)

- Local: `Data/Kaggle/diseases-symptoms-773/diseases-symptoms-773.csv` (~246.9K rows, ~377 symptoms, first column `diseases`)
- Upstream/license: TODO(user) — identify exact Kaggle source from your downloads and record license here
- Purpose: post-MVP scale-up candidate (not used in the MVP pipeline)
- Known caveat: symptom vocabulary differs from dataset #1; a mapping table will be required before any scale-up

## 3. Synthea synthetic patient sample

- Local: `Data/Synthea/*.csv` (full export: patients, encounters, conditions, observations, medications, allergies, procedures, immunizations, etc.)
- Generator: open-source Synthea (synthetichealth/synthea) — synthetic data, no real PHI
- License: generator is MIT; TODO(user) — note the distribution terms of the specific sample you obtained
- Purpose: end-to-end app testing only (Step 12 case generation). **Never** used for classifier training
- Note: SNOMED CT-coded conditions/observations do not map to binary symptom vectors; not classifier-compatible by design
