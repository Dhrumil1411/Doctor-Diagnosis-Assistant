from fastapi import FastAPI

from app.api.routes.auth import router as auth_router
from app.api.routes.health import router as health_router
from app.api.routes.users import router as users_router


def create_app() -> FastAPI:
    app = FastAPI(title="Doctor Diagnosis Assistant API", version="0.1.0")
    app.include_router(health_router)
    app.include_router(auth_router)
    app.include_router(users_router)
    return app


app = create_app()
