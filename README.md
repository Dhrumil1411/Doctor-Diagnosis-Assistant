# Doctor Diagnosis Assistant (DDA)

An intelligent clinical decision support workstation designed for general practice clinicians. DDA streamlines clinical intake, structures doctor-patient dialogues into standardized EHR schemas with Human Phenotype Ontology (HPO) codes, generates machine-learning disease probabilities across 773 conditions, and synthesizes multi-modal differential diagnoses via LLM clinical reasoning.

> [!WARNING]
> **Medical & Educational Disclaimer:**
> This project is a research prototype and technical demonstration developed using public and synthetic data (Kaggle disease-symptom datasets and Synthea patient simulations). It is **not** medical software, not certified by any health regulatory agency (such as the FDA or CE mark), and **does not provide medical advice, clinical diagnoses, or treatment plans**. Attending medical practitioners retain sole clinical judgment and responsibility for all patient evaluations.

---

## Architecture Overview

```mermaid
flowchart TD
    subgraph Client ["Client Layer"]
        UI["React 19 SPA (Vite)"]
        Forms["Intake Form & Note Extractor"]
        Decision["Attending Physician Sign-Off"]
    end

    subgraph Gateway ["Reverse Proxy & Rate Limiting"]
        NGINX["Nginx Container (:80)"]
        SlowAPI["SlowAPI Limiter (IP-keyed)"]
    end

    subgraph Backend ["FastAPI Core Services (:8000)"]
        Auth["JWT & RBAC Service (HS256 + Bcrypt)"]
        NLP["Clinical Note NLP & Heuristic Extractor"]
        Router["REST API Router (40 Endpoints)"]
        Audit["Database Audit Logger"]
        ReasonEngine["Differential Reasoning Engine"]
    end

    subgraph ML ["Diagnostic & Intelligence Layer"]
        Classifier["BernoulliNB Classifier (377 Features → 773 Classes)"]
        HPO["HPO Phenotype Normalizer & Synonym Registry"]
        LLMChain["LLM Fallback Chain (Groq ➔ OpenRouter)"]
        Cache["SHA-256 Payload LRU Cache (500 Entries)"]
    end

    subgraph Storage ["Persistence Layer"]
        Postgres[("PostgreSQL 17 / SQLite 3")]
        Uploads[("Diagnostic Lab Attachments")]
    end

    UI -->|HTTP / REST| NGINX
    NGINX -->|Proxy /api/| SlowAPI
    SlowAPI --> Router
    Router --> Auth
    Router --> NLP
    Router --> ReasonEngine
    Router --> Audit

    NLP --> HPO
    NLP --> LLMChain
    ReasonEngine --> Classifier
    ReasonEngine --> Cache
    ReasonEngine --> LLMChain

    Auth --> Postgres
    Router --> Postgres
    Audit --> Postgres
    Router --> Uploads
```

---

## Features

* **AI Clinical Note & Dialogue Extractor**: Paste raw doctor narratives, SOAP notes, or consultation transcripts to auto-populate patient demographics, vitals, OPQRST pain characteristics, and symptoms via an LLM extraction pipeline with deterministic regex fallback.
* **Standardized HPO Symptom Checklist**: Search and select from 377 clinical symptoms categorized by organ system and normalized to Human Phenotype Ontology (`HP:XXXXXXX`) concept IDs and colloquial synonyms.
* **773-Disease ML Classifier**: Fast statistical inference using a Bernoulli Naive Bayes model trained on 246,945 patient presentations, delivering Top-1, Top-5, and Top-10 disease likelihoods.
* **DDXPlus Clinical Evidence Reasoning**: Generates structured differentials ranking high/moderate/low likelihoods by evaluating antecedents (age, comorbidities, medications, social history) against active evidences, pertinent negatives, and emergency red flags.
* **Multi-Provider LLM Fallback & Caching**: Multi-provider resilience automatically cascading from Groq to OpenRouter with an in-memory SHA-256 canonical payload cache (500 entries) preventing redundant inference.
* **Diagnostic Lab & Imaging Reports**: Upload and attach multi-format clinical files (PDF, PNG, JPG, DICOM, TXT, DOCX) to patient visits with metadata aggregation.
* **Doctor Final Sign-off & Decision Tracking**: Dedicated review screen enabling attending physicians to accept, modify, or reject AI diagnostic recommendations with clinical rationales stored in the permanent medical record.
* **Enterprise Role-Based Access Control (RBAC)**: Enforces role permissions across `doctor`, `admin`, `nurse`, and `read_only` accounts using signed JWT bearer tokens and salted bcrypt password hashing.
* **Immutable Audit Trail**: Tracks user authentication, clinical record creation, differential generation, and patient updates with client IP addresses and serialized state diffs.
* **Automated Rate Limiting**: SlowAPI token bucket limiting protects high-compute endpoints (`/api/predict`, `/api/reason`, `/api/clinical-notes/extract`) against abuse.

---

## Tech Stack

| Layer | Technology | Purpose |
|---|---|---|
| **Frontend** | React 19, React Router DOM 7, Vite 8 | Single-page clinical workstation interface |
| **Testing (UI)** | Vitest 5, React Testing Library, JSDOM | Frontend unit and user-flow integration testing |
| **Backend** | Python 3.13, FastAPI 0.115, Uvicorn 0.30 | High-performance asynchronous REST API |
| **ORM & Migrations** | SQLAlchemy 2.0, Alembic 1.13 | Declarative database modeling and schema revisions |
| **Databases** | PostgreSQL 17 (Production/Docker), SQLite 3 (Dev/Test) | Relational persistence with 13 foreign-key constrained tables |
| **Security & Auth** | PyJWT (HS256), Bcrypt, SlowAPI | Token-based auth, password hashing, and rate limiting |
| **Machine Learning** | scikit-learn 1.5, pandas 2.0, NumPy, SciPy, Joblib | Binary classification, top-k evaluation, and artifact serialization |
| **LLM Inference** | Groq API, OpenRouter API, HTTPX | Structured JSON extraction and clinical reasoning |
| **Containerization** | Docker, Docker Compose, Nginx | Multi-container deployment (database, backend, frontend) |
| **CI / CD** | GitHub Actions | Automated Python test suites and frontend lint/test/build |

---

## Machine Learning & Evaluation

The diagnostic classifier models disease probabilities from high-dimensional binary symptom indicators across 773 acute and chronic clinical conditions.

### Dataset
* **Source:** Kaggle `diseases-symptoms-773` (`diseases-symptoms-773.csv`)
* **Raw Presentation Records:** 246,945 clinical records
* **Cleaned Training Set:** 197,559 records (80%)
* **Cleaned Test Set:** 49,386 records (20%)
* **Feature Dimensions:** 377 standardized symptom features
* **Class Space:** 773 disease categories

### Model Architecture & Benchmark
Multiple candidate classifiers were evaluated against a baseline floor:

| Model | Top-1 Accuracy | Top-5 Accuracy | Top-10 Accuracy | Precision (Macro) | Recall (Macro) | Macro-F1 | Training Time |
|---|---|---|---|---|---|---|---|
| **Dummy (Most Frequent)** | 0.49% | 1.28% | 1.85% | 0.00% | 0.14% | 0.00% | 0.32s |
| **Multinomial Naive Bayes** | 86.02% | 97.73% | 99.21% | 84.83% | 77.86% | 80.04% | 4.34s |
| **Bernoulli Naive Bayes (Champion)** | **87.00%** | **98.21%** | **99.37%** | **82.13%** | **80.49%** | **80.41%** | **3.53s** |

*(Verified from `ml/artifacts/metrics.json` generated on test set of 49,386 samples)*

---

## Environment Variables

Copy `.env.example` to `.env` in the repository root:

```bash
cp .env.example .env
```

| Variable | Default Value | Description |
|---|---|---|
| `APP_ENV` | `development` | Application runtime environment (`development`, `testing`, `production`) |
| `SECRET_KEY` | `dev-only-secret-...` | Cryptographic secret for signing JWT access tokens |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `480` | Lifetime of issued JWT authentication tokens (8 hours) |
| `DATABASE_URL` | `sqlite:///backend/dda.db` | SQLAlchemy connection string (supports SQLite and PostgreSQL) |
| `LLM_PROVIDER_CHAIN` | `groq,openrouter` | Comma-separated order of LLM providers for reasoning |
| `GROQ_API_KEY` | *(optional)* | API key for Groq Cloud completions |
| `GROQ_MODEL` | `openai/gpt-oss-120b` | Model name for Groq inference |
| `OPENROUTER_API_KEY` | *(optional)* | API key for OpenRouter completions |
| `OPENROUTER_MODEL` | `nvidia/nemotron-3-super-120b-a12b:free` | Model name for OpenRouter inference |
| `RATE_LIMIT_PREDICT` | `60/minute` | Rate limit for `/api/predict` |
| `RATE_LIMIT_REASON` | `30/minute` | Rate limit for `/api/reason` |
| `RATE_LIMIT_NOTE_EXTRACT` | `30/minute` | Rate limit for `/api/clinical-notes/extract` |

---

## Quick Start

### Option A: Docker Compose (Recommended)

Run PostgreSQL, FastAPI backend, and Nginx/React frontend in isolated containers:

```bash
# 1. Clone the repository
git clone https://github.com/Dhrumil1411/Doctor-Diagnosis-Assistant.git
cd Doctor-Diagnosis-Assistant

# 2. Configure environment
cp .env.example .env

# 3. Launch the container stack
docker compose up --build
```

* **Frontend UI:** `http://localhost:3000`
* **API Documentation (Swagger):** `http://localhost:8000/docs`
* **Health Check:** `http://localhost:8000/health`

---

### Option B: Manual Local Setup

#### 1. Backend Setup
```bash
# Set up Python virtual environment
python -m venv .venv
# Windows:
.\.venv\Scripts\activate
# Linux / macOS:
source .venv/bin/activate

# Install dependencies
pip install -r backend/requirements.txt -r ml/requirements.txt

# Run migrations (creates SQLite dda.db or initializes PostgreSQL)
cd backend
alembic upgrade head
cd ..

# Optional: Seed an administrative user
python backend/scripts/create_admin.py

# Launch backend server
uvicorn app.main:app --app-dir backend --reload --port 8000
```

#### 2. Frontend Setup
```bash
# In a separate terminal
cd frontend
npm install
npm run dev
```

Visit `http://localhost:5173` to access the Vite development workstation.

---

## API Endpoints

The backend provides 40 endpoints across 28 distinct routes:

| HTTP Method | Route Path | Access / Role | Description |
|---|---|---|---|
| `GET` | `/health` | Public | System status and database connectivity check |
| `POST` | `/api/auth/login` | Public | OAuth2 password login, returns JWT token |
| `GET` | `/api/auth/me` | Authenticated | Inspect current authenticated user and permissions |
| `GET` | `/api/users` | Admin | List all registered hospital users |
| `POST` | `/api/users` | Admin | Register new doctor, nurse, or staff account |
| `PATCH` | `/api/users/{user_id}` | Admin | Activate, deactivate, or modify staff roles |
| `GET` | `/api/patients` | All Roles | Search and list patient medical records |
| `POST` | `/api/patients` | Doctor, Nurse, Admin | Register new patient with MRN and consent |
| `GET` | `/api/patients/{id}` | All Roles | Retrieve comprehensive patient record and history |
| `PATCH` | `/api/patients/{id}` | Doctor, Nurse, Admin | Update patient demographics and contact details |
| `GET` | `/api/patients/{id}/visits` | All Roles | List all clinical encounter visits for patient |
| `GET` | `/api/patients/{id}/allergies` | All Roles | List documented drug and environmental allergies |
| `POST` | `/api/patients/{id}/allergies` | Doctor, Nurse, Admin | Record new patient allergy entry |
| `GET` | `/api/patients/{id}/history` | All Roles | Retrieve chronic medical and surgical history |
| `POST` | `/api/patients/{id}/history` | Doctor, Nurse, Admin | Append medical history record |
| `GET` | `/api/patients/{id}/medications` | All Roles | List active outpatient medication regimens |
| `POST` | `/api/patients/{id}/medications` | Doctor, Nurse, Admin | Prescribe or document patient medication |
| `POST` | `/api/visits` | Doctor, Nurse, Admin | Initiate new clinical consultation encounter |
| `GET` | `/api/visits/{id}` | All Roles | Fetch aggregated visit record (vitals, symptoms, notes) |
| `PATCH` | `/api/visits/{id}` | Doctor, Nurse, Admin | Update encounter notes and complaint details |
| `PUT` | `/api/visits/{id}/symptoms` | Doctor, Nurse, Admin | Replace active symptom list for visit |
| `PUT` | `/api/visits/{id}/vitals` | Doctor, Nurse, Admin | Upsert vital signs (BP, HR, temp, SpO2, pain) |
| `PUT` | `/api/visits/{id}/social-history` | Doctor, Nurse, Admin | Document personal habits, smoking, sleep, addictions |
| `PUT` | `/api/visits/{id}/general-exam` | Doctor, Nurse, Admin | Upsert physical examination findings (pallor, edema, etc.) |
| `GET` | `/api/visits/{id}/labs` | All Roles | List diagnostic lab tests and attached files |
| `POST` | `/api/visits/{id}/labs` | Doctor, Nurse, Admin | Upload diagnostic lab reports or imaging studies |
| `DELETE` | `/api/labs/{id}` | Doctor, Nurse, Admin | Delete uploaded lab report attachment |
| `GET` | `/api/symptom-vocabulary` | Public / All | Retrieve 377 symptom vocabulary with HPO metadata |
| `POST` | `/api/clinical-notes/extract` | Doctor, Nurse, Admin | NLP entity extraction from raw doctor notes *(Rate-limited)* |
| `POST` | `/api/predict` | Doctor, Nurse, Admin | 773-class Bayesian classifier prediction *(Rate-limited)* |
| `POST` | `/api/reason` | Doctor, Nurse, Admin | LLM differential diagnosis reasoning engine *(Rate-limited)* |
| `GET` | `/api/visits/{id}/diagnosis` | All Roles | Fetch signed clinical decision record |
| `POST` | `/api/visits/{id}/diagnosis` | Doctor, Nurse, Admin | Record attending physician diagnosis and sign-off |
| `GET` | `/api/audit-logs` | Admin | Searchable audit log of data mutations and logins |

---

## Deployment

For public or production deployment (Render, Railway, Fly.io, AWS, GCP, or a VPS with Docker):

### Required Environment Variables

When `APP_ENV=production`, strict startup validation prevents execution if secrets are missing or retain development defaults:

| Variable | Required in Production | Description |
|---|:---:|---|
| `APP_ENV` | Yes | Set to `production`. Activates strict secret validation and disables debug behavior. |
| `JWT_SECRET` | Yes | High-entropy random secret (minimum 32 characters) used to sign and verify JWT authentication tokens. **FastAPI fails startup immediately** if this is missing or set to a placeholder (`dev-only-...`, `change-me-...`). |
| `DATABASE_URL` | Yes | PostgreSQL connection string (e.g., `postgresql+psycopg://user:password@host:5432/dbname?sslmode=require`). Alembic migrations execute automatically on container startup. |

### Optional / Integration Environment Variables

| Variable | Default | Description |
|---|---|---|
| `CORS_ORIGINS` | `http://localhost:5173,...` | Comma-separated list of allowed web origins (e.g., `https://dda.example.com,https://dda-frontend.onrender.com`). |
| `FORWARDED_ALLOW_IPS` | `*` | IP addresses trusted by Uvicorn proxy headers for resolving `X-Forwarded-For`. |
| `SEED_DEMO` | `false` | When set to `true`, executes idempotent demo seeding on container launch (creates demo staff accounts and synthetic patient cases). |
| `DEMO_DOCTOR_PASSWORD` | *(local default only)* | Custom password for `demo.doctor@example.com` when `SEED_DEMO=true`. |
| `DEMO_READONLY_PASSWORD` | *(local default only)* | Custom password for `demo.nurse@example.com` when `SEED_DEMO=true`. |
| `DEMO_ADMIN_PASSWORD` | *(local default only)* | Custom password for `demo.admin@example.com` when `SEED_DEMO=true`. |
| `GROQ_API_KEY` | *(empty)* | Optional API key for Groq inference provider (`openai/gpt-oss-120b`). |
| `OPENROUTER_API_KEY` | *(empty)* | Optional API key for OpenRouter inference provider (`nvidia/nemotron-3.5-lightning:free`). |
| `VITE_API_URL` | *(empty = same-origin `/api`)* | Base API URL for frontend build (set if frontend and backend are hosted on distinct domains). |
| `VITE_DEMO_MODE` | `false` | When set to `true`, displays persistent demo disclaimers in the navbar and login card. |

---

## Running Test Suites

### Backend Tests (pytest)
```bash
# Run all 77 automated backend tests
pytest backend/tests -v

# Run rate limiting tests
pytest backend/tests/test_rate_limit.py -v

# Run end-to-end clinical workflow scenarios
pytest backend/tests/test_e2e_scenarios.py -v
```

### Frontend Tests (Vitest & React Testing Library)
```bash
cd frontend

# Run all 10 unit and integration tests
npm test

# Run linter
npm run lint

# Validate production build bundle
npm run build
```

---

## License

Distributed under the Apache 2.0 License. See `LICENSE` for details.
