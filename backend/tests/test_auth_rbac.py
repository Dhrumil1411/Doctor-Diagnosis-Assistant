import uuid

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.core.security import create_access_token
from app.db.base import SessionLocal
from app.models.audit_log import AuditLog
from app.models.users import User, UserRole
from tests.conftest import PASSWORD, login, make_user


def test_login_wrong_password(client: TestClient, admin_user: User):
    resp = login(client, admin_user.email, "wrong-password")
    assert resp.status_code == 401


def test_login_unknown_email(client: TestClient):
    resp = login(client, "nobody@nowhere.local")
    assert resp.status_code == 401


def test_login_success_returns_token(client: TestClient, admin_user: User):
    resp = login(client, admin_user.email)
    assert resp.status_code == 200
    body = resp.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]


def test_me_requires_token(client: TestClient):
    assert client.get("/api/auth/me").status_code == 401


def test_me_rejects_garbage_token(client: TestClient):
    resp = client.get("/api/auth/me", headers={"Authorization": "Bearer not-a-jwt"})
    assert resp.status_code == 401


def test_me_returns_current_user(client: TestClient, admin_headers):
    resp = client.get("/api/auth/me", headers=admin_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["role"] == "admin"
    assert body["is_active"] is True


def test_users_list_admin_only(client: TestClient, doctor_headers):
    assert client.get("/api/users", headers=doctor_headers).status_code == 403
    assert client.get("/api/users").status_code == 401


def test_admin_can_create_doctor(client: TestClient, admin_headers):
    payload = {
        "email": f"{uuid.uuid4().hex[:12]}@example.com",
        "password": "Doctor!2345",
        "full_name": "Created Doctor",
        "role": "doctor",
    }
    resp = client.post("/api/users", json=payload, headers=admin_headers)
    assert resp.status_code == 201
    assert resp.json()["role"] == "doctor"
    assert "hashed_password" not in resp.json()

    dup = client.post("/api/users", json=payload, headers=admin_headers)
    assert dup.status_code == 409


def test_create_user_rejects_short_password(client: TestClient, admin_headers):
    resp = client.post(
        "/api/users",
        json={
            "email": f"{uuid.uuid4().hex[:12]}@example.com",
            "password": "short",
            "full_name": "Bad Pw",
            "role": "doctor",
        },
        headers=admin_headers,
    )
    assert resp.status_code == 422


def test_created_doctor_can_login(client: TestClient, admin_headers):
    email = f"{uuid.uuid4().hex[:12]}@example.com"
    resp = client.post(
        "/api/users",
        json={"email": email, "password": "Doctor!2345", "full_name": "D"},
        headers=admin_headers,
    )
    assert resp.status_code == 201
    assert login(client, email, "Doctor!2345").status_code == 200


def test_admin_cannot_demote_or_disable_self(
    client: TestClient, admin_headers, admin_user: User
):
    resp_role = client.patch(
        f"/api/users/{admin_user.id}", json={"role": "doctor"}, headers=admin_headers
    )
    assert resp_role.status_code == 400

    resp_active = client.patch(
        f"/api/users/{admin_user.id}", json={"is_active": False}, headers=admin_headers
    )
    assert resp_active.status_code == 400


def test_admin_can_change_other_users(client: TestClient, admin_headers):
    nurse = make_user(UserRole.nurse)
    resp = client.patch(
        f"/api/users/{nurse.id}", json={"is_active": False}, headers=admin_headers
    )
    assert resp.status_code == 200
    assert resp.json()["is_active"] is False


def test_deactivated_user_cannot_login(client: TestClient, admin_headers):
    user = make_user(UserRole.doctor)
    client.patch(
        f"/api/users/{user.id}", json={"is_active": False}, headers=admin_headers
    )
    assert login(client, user.email).status_code == 403


def test_token_of_deactivated_user_is_rejected(
    client: TestClient, doctor_headers, doctor_user: User, admin_headers
):
    assert client.get("/api/auth/me", headers=doctor_headers).status_code == 200
    client.patch(
        f"/api/users/{doctor_user.id}",
        json={"is_active": False},
        headers=admin_headers,
    )
    resp = client.get("/api/auth/me", headers=doctor_headers)
    assert resp.status_code == 401


def test_missing_user_id_in_db_rejected(client: TestClient):
    ghost_id = uuid.uuid4()
    token = create_access_token(ghost_id, "admin")
    resp = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 401


def test_audit_log_records_auth_events(admin_headers, admin_user: User):
    db = SessionLocal()
    try:
        events = db.scalars(
            select(AuditLog.action).where(AuditLog.actor_user_id == admin_user.id)
        ).all()
        assert "login_success" in events
    finally:
        db.close()


def test_health_still_open_without_auth(client: TestClient):
    assert client.get("/health").status_code == 200
