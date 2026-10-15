# Doctor Diagnosis Assistant

An intelligent clinical decision support platform designed to assist medical practitioners with structured patient intake, machine learning disease predictions, standardized Human Phenotype Ontology (HPO) mapping, and AI-powered differential diagnoses.

> **Status: Phase 1 & Architecture Scale-up Complete** — 773 Diseases / 377 Symptoms, HPO Standardized Phenotypes, DDXPlus Clinical Evidence Framework. **70 automated tests passing (100% green)**.
> 
> 🩺 **Doctor Colleague Overview**: See [CLINICAL_OVERVIEW.md](CLINICAL_OVERVIEW.md) for a clinical-friendly summary of the system and future medical roadmap.

---

## Features

| Feature | Details |
|---|---|
| **Patient Intake Form** | Demographics, vitals (auto-BMI), OPQRST HPI, searchable HPO symptom checklist with severity/duration, allergies, medications, social history, working notes |
| **ML Disease Classifier** | BernoulliNB (377 symptoms → 773 diseases, 87.0% Top-1, 97.8% Top-5, 99.4% Top-10); top-ranked differential predictions with confidence probabilities |
| **HPO Phenotype Layer** | Standardized Human Phenotype Ontology (`HP:XXXXXXX`) mappings, colloquial synonym normalization, and domain-based category filtering |
| **LLM Reasoning Layer** | DDXPlus Clinical Evidence Framework (Antecedents vs Active Evidences vs Pertinent Negatives); Groq → OpenRouter provider chain with auto-fallback |
| **Lab & Imaging Upload** | File attachment (PDF, PNG, JPG, DICOM, TXT, DOC, up to 10 MB); lab findings injected into LLM reasoning; per-visit lab management with delete |
| **Doctor Feedback Workflow** | Accept, edit, or reject algorithmic diagnoses with notes; accepted/edited decision stored with final disease label |
| **Role-Based Access Control** | Doctor / Admin / Nurse / Read-Only roles; JWT authentication; admin-only user management |
| **Audit Log Viewer** | Admin-only paginated audit log UI; filterable by action type, entity type, and actor; expandable JSON detail inspector |
| **End-to-End Test Suite** | Synthea synthetic data loader + curated multi-domain clinical benchmark cases; 70 automated integration tests |

---

## Tech Stack

| Layer | Technologies |
|---|---|
| **Backend** | Python 3.13, FastAPI, Uvicorn, SQLAlchemy 2.0, Alembic, Pydantic v2, PyJWT, Bcrypt, HTTPX, Pytest |
| **Database** | PostgreSQL 17 (via Docker Compose) |
| **Frontend** | JavaScript (ES6+), React 19, React Router DOM v7, Vite 6, Oxlint |
| **ML / AI** | Scikit-learn (Logistic Regression), Joblib, Groq API, OpenRouter API |

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────┐
│                  React SPA (Vite)                   │
│  Login → Intake Form → Results → Audit Logs         │
└──────────────────┬──────────────────────────────────┘
                   │ HTTP (Vite dev proxy / nginx)
┌──────────────────▼──────────────────────────────────┐
│              FastAPI Backend (:8000)                 │
│  /api/auth  /api/patients  /api/visits               │
│  /api/predict  /api/reason  /api/audit-logs          │
└────────┬────────────┬──────────────┬────────────────┘
         │            │              │
    ┌────▼────┐  ┌────▼────┐  ┌─────▼──────┐
    │PostgreSQL│  │ joblib  │  │ Groq /     │
    │   DB     │  │ model   │  │ OpenRouter  │
    └──────────┘  └─────────┘  └────────────┘
```

---

## API Endpoints Summary

| Method | Path | Role | Description |
|---|---|---|---|
| POST | `/api/auth/login` | Public | JWT login |
| GET | `/api/auth/me` | Any | Current user info |
| GET/POST/PATCH | `/api/users` | Admin | User management |
| GET/POST | `/api/patients` | Any/Writer | Patient list & create |
| GET/PATCH | `/api/patients/{id}` | Any/Writer | Patient detail & update |
| GET/POST | `/api/visits` | Any/Writer | Visit list & create |
| GET | `/api/visits/{id}` | Any | Visit detail (aggregated) |
| POST | `/api/predict` | Writer | ML classifier inference |
| POST | `/api/reason` | Writer | LLM differential reasoning |
| POST/GET | `/api/visits/{id}/diagnosis` | Writer/Any | Doctor feedback |
| POST/GET | `/api/visits/{id}/labs` | Writer/Any | Lab upload & list |
| DELETE | `/api/labs/{id}` | Writer | Delete lab attachment |
| GET | `/api/audit-logs` | Admin | Paginated audit log |
| GET | `/api/symptom-vocabulary` | Any | Symptom list for intake form |

---

## Quick Start

### Prerequisites
- Python 3.11+ (tested on 3.13)
- Node.js 20+ and npm
- Docker Desktop with WSL2 (for PostgreSQL)
- Free API keys: [Groq](https://console.groq.com) and [OpenRouter](https://openrouter.ai)

### 1. Clone & configure

```bash
git clone <repo-url>
cd Doctor-Diagnosis-Assistant

# Copy env template and fill in values
cp .env.example .env
# Edit .env: set DATABASE_URL, JWT_SECRET_KEY, GROQ_API_KEY, OPENROUTER_API_KEY
```

### 2. Backend setup

```bash
# Create and activate virtual environment
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # Linux/Mac

pip install -r backend/requirements.txt

# Start PostgreSQL
docker compose up -d

# Apply migrations
cd backend
alembic upgrade head

# Seed admin user
python scripts/create_admin.py

# Start backend server
uvicorn app.main:app --reload --port 8000
```

### 3. Frontend setup

```bash
# In a new terminal
cd frontend
npm install
npm run dev
```

Access the app at `http://localhost:5173`.

---

## Running Tests

```bash
cd backend

# Run full test suite (63 tests)
..\.venv\Scripts\python.exe -m pytest

# Run with verbose output
..\.venv\Scripts\python.exe -m pytest -v

# Run a specific test file
..\.venv\Scripts\python.exe -m pytest tests/test_audit.py -v

# Run end-to-end scenarios only
..\.venv\Scripts\python.exe -m pytest tests/test_e2e_scenarios.py -v
```

---

## Project Structure

```
Doctor-Diagnosis-Assistant/
├── backend/
│   ├── app/
│   │   ├── api/routes/        # FastAPI route handlers
│   │   ├── models/            # SQLAlchemy ORM models
│   │   ├── schemas/           # Pydantic request/response schemas
│   │   ├── services/          # Business logic (classifier, audit, LLM)
│   │   └── e2e/               # E2E test data loaders (Synthea + curated)
│   ├── migrations/            # Alembic migration scripts
│   ├── scripts/               # Utility scripts (create_admin, run_e2e_suite)
│   └── tests/                 # Pytest test suite (63 tests)
├── frontend/
│   └── src/
│       ├── pages/             # React page components
│       ├── components/        # Reusable UI components
│       └── api/               # Fetch-based API client
├── ml/
│   ├── artifacts/             # Trained model + vocabulary (committed)
│   └── data_prep.py           # Data cleaning + model training pipeline
├── docs/                      # Dataset notes, data sources, compliance
├── uploads/                   # Lab file storage (gitignored)
└── docker-compose.yml
```

---

## Development Steps Completed

| Step | What |
|---|---|
| 0 | Repo scaffold, tooling baseline |
| 1 | Data audit + prep (42-disease Kaggle set) |
| 2 | Baseline classifier (Logistic Regression, CV + test macro-F1 = 1.00) |
| 3 | API skeleton + full DB schema + Alembic migrations |
| 4 | Auth + RBAC (Doctor/Admin/Nurse/Read-Only) + JWT |
| 5 | Patients/visits CRUD (full intake form persistence) |
| 6 | Classifier inference service (`POST /api/predict`) |
| 7 | LLM reasoning layer with Groq/OpenRouter fallback chain + cache |
| 8 | Frontend skeleton (Vite + React), login wired |
| 9 | Intake form UI (all 10 spec sections) |
| 10 | Results screen + accept/edit/reject feedback loop |
| 11 | Labs/imaging upload + LLM integration |
| 12 | End-to-end testing (Synthea loader + curated clinical benchmark) |
| 13 | Hardening: admin audit log viewer, DPDP compliance notes, docs finalized |

