import os
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.core.config import get_settings

from app.api.routes.audit import router as audit_router
from app.api.routes.auth import router as auth_router
from app.api.routes.diagnoses import router as diagnoses_router
from app.api.routes.health import router as health_router
from app.api.routes.labs import router as labs_router
from app.api.routes.note_extractor import router as note_extractor_router
from app.api.routes.patients import router as patients_router
from app.api.routes.predict import router as predict_router
from app.api.routes.reason import router as reason_router
from app.api.routes.users import router as users_router
from app.api.routes.visits import router as visits_router
from app.api.routes.vocabulary import router as vocabulary_router
from app.core.limiter import limiter


def create_app() -> FastAPI:
    app = FastAPI(title="Doctor Diagnosis Assistant API", version="0.1.0")

    settings = get_settings()
    origins = settings.cors_origins_list
    if origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=origins,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    # Ensure uploads directory exists and mount static files
    uploads_dir = Path("uploads")
    uploads_dir.mkdir(parents=True, exist_ok=True)
    app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

    app.include_router(health_router)
    app.include_router(auth_router)
    app.include_router(users_router)
    app.include_router(audit_router)
    app.include_router(patients_router)
    app.include_router(visits_router)
    app.include_router(labs_router)
    app.include_router(predict_router)
    app.include_router(reason_router)
    app.include_router(vocabulary_router)
    app.include_router(diagnoses_router)
    app.include_router(note_extractor_router)
    return app


app = create_app()
