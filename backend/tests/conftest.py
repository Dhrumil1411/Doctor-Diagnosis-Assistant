import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.core.security import hash_password
from app.db.base import SessionLocal
from app.main import app
from app.models.users import User, UserRole

PASSWORD = "Passw0rd!test"


def make_user(role: UserRole) -> User:
    db = SessionLocal()
    try:
        user = User(
            email=f"{uuid.uuid4().hex[:12]}@example.com",
            hashed_password=hash_password(PASSWORD),
            full_name=f"Test {role.value}",
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
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture(scope="session")
def admin_user():
    return make_user(UserRole.admin)


@pytest.fixture(scope="session")
def doctor_user():
    return make_user(UserRole.doctor)


@pytest.fixture(scope="session")
def nurse_user():
    return make_user(UserRole.nurse)


@pytest.fixture(scope="session")
def readonly_headers(client):
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
