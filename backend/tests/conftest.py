import os
import uuid
from typing import TYPE_CHECKING

import pytest
from fastapi.testclient import TestClient

if TYPE_CHECKING:
    from app.models.users import User, UserRole

PASSWORD = "Passw0rd!test"


@pytest.fixture(scope="session", autouse=True)
def setup_test_db(tmp_path_factory):
    # 1. Point DATABASE_URL at a temporary SQLite file
    test_db_dir = tmp_path_factory.mktemp("test_db")
    test_db_path = test_db_dir / "test.db"
    test_db_url = f"sqlite:///{test_db_path.as_posix()}"

    os.environ["DATABASE_URL"] = test_db_url
    os.environ["APP_ENV"] = "testing"

    # 2. Clear settings cache so get_settings() loads the temp DB URL
    from app.core.config import get_settings
    get_settings.cache_clear()

    # 3. Configure app.db.base engine and SessionLocal with the temp SQLite DB
    import app.db.base
    from sqlalchemy import create_engine
    test_engine = create_engine(test_db_url, pool_pre_ping=True)
    app.db.base.engine = test_engine
    app.db.base.SessionLocal.configure(bind=test_engine)

    # 4. Create all database tables on the temp DB
    import app.models  # noqa: F401
    from app.db.base import Base

    Base.metadata.create_all(bind=test_engine)

    yield test_engine

    # 5. Cleanup on session end
    Base.metadata.drop_all(bind=test_engine)
    test_engine.dispose()
    get_settings.cache_clear()


def make_user(role) -> "User":
    from app.core.security import hash_password
    from app.db.base import SessionLocal
    from app.models.users import User

    db = SessionLocal()
    try:
        user = User(
            email=f"{uuid.uuid4().hex[:12]}@example.com",
            hashed_password=hash_password(PASSWORD),
            full_name=f"Test {role.value if hasattr(role, 'value') else role}",
            role=role,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return user
    finally:
        db.close()


def login(client: TestClient, email: str, password: str = PASSWORD):
    return client.post(
        "/api/auth/login", data={"username": email, "password": password}
    )


@pytest.fixture(scope="session")
def client():
    from app.main import app
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture(scope="session")
def admin_user():
    from app.models.users import UserRole
    return make_user(UserRole.admin)


@pytest.fixture(scope="session")
def doctor_user():
    from app.models.users import UserRole
    return make_user(UserRole.doctor)


@pytest.fixture(scope="session")
def nurse_user():
    from app.models.users import UserRole
    return make_user(UserRole.nurse)


@pytest.fixture(scope="session")
def readonly_headers(client):
    from app.models.users import UserRole
    user = make_user(UserRole.read_only)
    resp = login(client, user.email)
    assert resp.status_code == 200
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


@pytest.fixture(scope="session")
def admin_headers(client, admin_user):
    resp = login(client, admin_user.email)
    assert resp.status_code == 200
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


@pytest.fixture(scope="session")
def doctor_headers(client, doctor_user):
    resp = login(client, doctor_user.email)
    assert resp.status_code == 200
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


@pytest.fixture(scope="session")
def nurse_headers(client, nurse_user):
    resp = login(client, nurse_user.email)
    assert resp.status_code == 200
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}
