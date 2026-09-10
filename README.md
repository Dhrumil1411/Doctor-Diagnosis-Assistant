# Doctor Diagnosis Assistant

An intelligent clinical decision support platform designed to assist medical practitioners with structured patient intake, machine learning disease predictions, and AI-powered differential diagnoses.

## Features
- Comprehensive patient intake form capturing demographics, vitals (with auto-BMI calculation), OPQRST history of present illness, and medical history
- Searchable symptom checklist mapped to structured medical vocabularies with severity and duration tracking
- Machine learning disease classifier offering instant top-ranked differential predictions with confidence probabilities
- LLM reasoning layer combining case details, vitals, red flags, and classifier outputs with automatic provider fallback (Groq / OpenRouter)
- Lab and imaging attachment management supporting file uploads (.pdf, .png, .jpg, .dicom, .txt, .doc) with dynamic case integration
- Role-based access control (Doctor, Admin, Nurse, Read-Only) with JWT authentication and audit logging
- Doctor feedback workflow to accept, edit, or override algorithmic diagnoses

## Tech Stack
- **Backend**: Python, FastAPI, Uvicorn, SQLAlchemy 2.0, PostgreSQL (via Docker) / SQLite, Alembic migrations, Pydantic v2, PyJWT, Bcrypt, HTTPX, Pytest
- **Frontend**: JavaScript (ES6+), React 19, React Router DOM v7, Vite, Oxlint
- **Machine Learning & AI**: Scikit-learn (Logistic Regression classifier), Joblib, Groq API & OpenRouter API

## How to Run
### 1. Backend Setup
1. Open a terminal and navigate to the project root:
   ```bash
   python -m venv .venv
   # Activate venv: .venv\Scripts\activate (Windows) or source .venv/bin/activate (Linux/Mac)
   pip install -r backend/requirements.txt
   ```
2. Configure `.env` in the root folder with database credentials and API keys (refer to `.env.example`).
3. Start the PostgreSQL database (e.g., `docker compose up -d`).
4. Apply database migrations:
   ```bash
   cd backend
   alembic upgrade head
   ```
5. Seed initial admin user:
   ```bash
   python scripts/create_admin.py
   ```
6. Start the FastAPI backend server:
   ```bash
   uvicorn app.main:app --reload --port 8000
   ```

### 2. Frontend Setup
1. In a separate terminal:
   ```bash
   cd frontend
   npm install
   npm run dev
   ```
2. Access the web interface at `http://localhost:5173`.

## Status
In progress (Phases A, B, and Phase C Steps 8–11 completed; end-to-end evaluation and audit viewer pending)
