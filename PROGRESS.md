# PROGRESS — Doctor Diagnosis Assistant

Single source of truth for build status across sessions. Update the step table and Decisions Log as work completes.
Reference docs: `project-roadmap.md` (authoritative) · `doctor-diagnosis-assistant-spec.md` (background).

**Rules of engagement:** one step at a time · next step starts only after explicit user confirmation · every completed step is committed.

## Status legend

`not started` → `in progress` → `done`

## Phase A — Foundations

| Step | What | Status |
|---|---|---|
| 0 | Repo scaffold, PROGRESS.md, tooling baseline | **done** (2026-08-23) — see Decisions Log; Docker flagged missing |
| 1 | Data audit + prep (42-disease set), symptom vocabulary | **done** (2026-08-23) — actual data: 131 symptoms / 41 diseases, see docs/dataset-notes.md |
| 2 | Baseline classifier (LR vs RF), champion model saved | **done** (2026-08-23) — champion: logistic regression; CV + test both 1.00 macro-F1 (see caveat below) |

## Phase B — Backend

| Step | What | Status |
|---|---|---|
| 3 | API skeleton + full DB schema + migrations | **in progress** — all code written & import-tested; BLOCKED on Docker/WSL2 install (user handling); remaining: `docker compose up -d --wait` → `alembic revision --autogenerate` → `alembic upgrade head` → `/health` smoke test |
| 4 | Auth + RBAC (doctor/admin) | not started |
| 5 | Patients/visits CRUD (form sections 5.1–5.9 + 5.12 persistence) | not started |
| 6 | Classifier inference service (`POST /api/predict`) | not started |
| 7 | LLM reasoning layer — provider chain w/ fallback + cache (`POST /api/reason`) | not started |

## Phase C — Frontend & Integration

| Step | What | Status |
|---|---|---|
| 8 | Frontend skeleton (Vite + React), login wired | not started |
| 9 | Intake form UI (sections 5.1–5.9 + notes) | not started |
| 10 | Results screen + accept/edit/reject feedback loop | not started |
| 11 | Labs/imaging upload *(skippable if user wants testing sooner)* | not started |
| 12 | End-to-end testing — Synthea-generated + curated fictional cases | not started |
| 13 | Hardening, audit-log viewer, docs/README finalization | not started |

## Decisions Log

| Date | Decision | Rationale |
|---|---|---|
| 2026-08-23 | Stack: FastAPI + Vite/React SPA + PostgreSQL (via Docker) + git from Step 0 | One language for API+ML (FastAPI); simple SPA for form-heavy internal tool; clean DB lifecycle via Docker |
| 2026-08-23 | Scope: general-medicine MVP; structured symptom entry only (no free-text NLP); macro-F1 as model-selection metric | Roadmap open questions resolved; Symptom2Disease dataset not present in Data/ anyway |
| 2026-08-23 | Classifier data: use Kaggle Training/Testing split AS-IS (never merge/re-split — near-duplicate leakage risk); CV within Training for selection; single final eval on Testing | User instruction + source-data near-duplicate warning |
| 2026-08-23 | LLM layer: provider chain `groq → openrouter` behind one OpenAI-compatible client; auto-fallback on 429/error; response cache keyed by case content; lean prompts | Gemini free-tier quota exhaustion was the pain point; stacking two free quotas + cache removes it; Groq gives stronger reasoners (Llama 3.3 70B / GPT-OSS 120B) |
| 2026-08-23 | Node/npm project init deferred to Step 8 (Vite scaffold owns package.json); root venv shared by backend+ml | Avoids throwaway config Vite would overwrite; single Python env keeps student setup simple |
| 2026-08-23 | `Data/` gitignored (large source files stay local); sources/licenses to be documented in `docs/data-sources.md` at Step 1 | Standard practice; reproducibility preserved via documented sources + prep scripts |
| 2026-08-23 | Cleaned train/test CSVs + vocabulary + prep_report are COMMITTED in `ml/artifacts/` (regenerable via `ml/data_prep.py`) | Decouples Steps 2+ from raw `Data/` presence; ~1 MB total; generator script is the source of truth |
| 2026-08-23 | Dataset reality recorded as 131 symptoms / 41 diseases (not advertised 132/42) — duplicate column name double-counted upstream, and only 41 classes exist in the files | Verified by audit; assertions in data_prep.py now derive expectations from raw shape, not folklore |
| 2026-08-23 | Champion = logistic regression (LR and RF tied at CV macro-F1 1.000; LR preferred: interpretable coefficients, tiny artifact, fast inference). Dummy floor included (macro-F1 0.0012) to guard against misleading accuracy | Pre-agreed macro-F1 rule + simplicity tie-break |
| 2026-08-23 | Perfect scores treated as dataset property, NOT model quality claim — source data is near-deterministic per disease. Classifier's real role: fast baseline cross-check for the LLM layer; partial-symptom behavior verified degrading gracefully | Honest reporting per roadmap "accuracy alone is misleading" |
| 2026-08-23 | DB enums as VARCHAR + CHECK (`native_enum=False`) instead of Postgres native types — adding values later needs no `ALTER TYPE` migration dance. DB bring-up deferred to user (WSL2 install pending); alembic initial revision will be autogenerated against live DB then | Student-project pragmatism; unblocks everything else |
| 2026-08-23 | Docker Desktop found as per-user winget install (`%LOCALAPPDATA%\Programs\DockerDesktop`), NOT on PATH; engine requires WSL2 which is not installed. User opted to handle WSL2/Docker setup themselves later | Root-caused in Step 3; no code impact |

## Known data quirks (verified in Step-1 audit — full detail in docs/dataset-notes.md)

- Duplicate `fluid_overload` column: first twin is ALL-ZERO dead col, all 114 positives in second → OR-merged (naive keep-first would lose data)
- Phantom `Unnamed: 133` col in Training (trailing comma artifact, 0 non-null) → dropped
- Space-broken names ×3 (`spotting_ urination`, etc.) and padded labels `'Diabetes '`, `'Hypertension '` → normalized
- **Testing.csv = 42 rows over 41 classes** (several classes n=1) → per-class test metrics are noise: select via stratified CV on training, touch test once at end of Step 2
- Missing vs roadmap: Symptom2Disease + Synthetic-8 datasets absent locally → scale-up target = diseases-symptoms-773 (post-MVP backlog)
- Synthea ≠ binary symptom vectors → used for realistic e2e case generation only (Step 12), never classifier training

## Open items / pending decisions

- [ ] **User:** install WSL2 (`wsl --install --no-distribution` from an ADMIN PowerShell, approve UAC, reboot when asked), then start Docker Desktop → tell me and I'll finish Step 3 bring-up (~2 min)
- [x] ~~User: install Docker Desktop~~ — installed (per-user winget, v29.7.2); engine blocked on WSL2 only
- [ ] **User:** create free Groq + OpenRouter API keys before Step 7 (email-only signup, no card)
- [ ] **User:** fill license fields in `docs/data-sources.md` from your Kaggle download history (low priority, before Step 13)
- [ ] Step 11 decision: local-disk storage vs real S3 bucket for lab uploads
