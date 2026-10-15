import uuid
import pytest
from fastapi.testclient import TestClient

from app.db.base import SessionLocal
from app.services.audit import record_audit


def test_audit_logs_admin_access_and_pagination(client: TestClient, admin_headers, admin_user):
    db = SessionLocal()
    try:
        # Generate some audit entries
        unique_action = f"test_act_{uuid.uuid4().hex[:6]}"
        record_audit(
            db,
            actor_user_id=admin_user.id,
            action=unique_action,
            entity_type="test_entity",
            detail={"key": "val"},
        )
        db.commit()
    finally:
        db.close()

    # Query without filters
    resp = client.get("/api/audit-logs", headers=admin_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data
    assert "total" in data
    assert data["total"] >= 1
    assert data["limit"] == 50
    assert data["offset"] == 0

    # Query with action filter
    filtered_resp = client.get(f"/api/audit-logs?action={unique_action}", headers=admin_headers)
    assert filtered_resp.status_code == 200
    f_data = filtered_resp.json()
    assert f_data["total"] >= 1
    assert f_data["items"][0]["action"] == unique_action
    assert f_data["items"][0]["actor_email"] == admin_user.email
    assert f_data["items"][0]["detail"] == {"key": "val"}


def test_audit_logs_rbac_enforcement(client: TestClient, doctor_headers, nurse_headers, readonly_headers):
    # Doctors, nurses, and readonly users must be rejected with 403 Forbidden
    for headers in [doctor_headers, nurse_headers, readonly_headers]:
        resp = client.get("/api/audit-logs", headers=headers)
        assert resp.status_code == 403

    # Unauthenticated must be rejected with 401 Unauthorized
    unauth_resp = client.get("/api/audit-logs")
    assert unauth_resp.status_code == 401
