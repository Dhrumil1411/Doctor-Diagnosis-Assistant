import io
import uuid
import pytest


def _create_patient(client, headers):
    resp = client.post(
        "/api/patients",
        json={
            "full_name": f"Lab Test Patient {uuid.uuid4().hex[:6]}",
            "sex": "female",
            "date_of_birth": "1990-05-15",
        },
        headers=headers,
    )
    assert resp.status_code == 201
    return resp.json()["id"]


def _create_visit(client, patient_id, headers):
    resp = client.post(
        "/api/visits",
        json={
            "patient_id": patient_id,
            "visit_type": "new",
            "chief_complaint": "Chest pain and fatigue",
        },
        headers=headers,
    )
    assert resp.status_code == 201
    return resp.json()["id"]


def test_create_lab_result_without_file(client, doctor_headers):
    pid = _create_patient(client, doctor_headers)
    vid = _create_visit(client, pid, doctor_headers)

    resp = client.post(
        f"/api/visits/{vid}/labs",
        data={
            "category": "blood",
            "test_name": "Complete Blood Count (CBC)",
            "result_summary": "Hb: 13.5 g/dL, WBC: 7,500 /uL, Platelets: 250k",
            "performed_at": "2026-09-01T10:00:00",
        },
        headers=doctor_headers,
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["visit_id"] == vid
    assert data["category"] == "blood"
    assert data["test_name"] == "Complete Blood Count (CBC)"
    assert data["file_path"] is None
    assert data["file_url"] is None


def test_create_lab_result_with_file_upload(client, doctor_headers):
    pid = _create_patient(client, doctor_headers)
    vid = _create_visit(client, pid, doctor_headers)

    fake_file_content = b"Sample Lab Report Text Document\nResults: Normal"
    file_tuple = ("chest_xray.txt", io.BytesIO(fake_file_content), "text/plain")

    resp = client.post(
        f"/api/visits/{vid}/labs",
        data={
            "category": "imaging",
            "test_name": "Chest X-Ray AP/PA",
            "result_summary": "Clear lung fields, no cardiomegaly",
        },
        files={"file": file_tuple},
        headers=doctor_headers,
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["category"] == "imaging"
    assert data["test_name"] == "Chest X-Ray AP/PA"
    assert data["file_path"] is not None
    assert data["file_url"] is not None
    assert "/uploads/labs/" in data["file_url"]

    # Verify static file download
    file_resp = client.get(data["file_url"])
    assert file_resp.status_code == 200
    assert file_resp.content == fake_file_content


def test_create_lab_invalid_extension(client, doctor_headers):
    pid = _create_patient(client, doctor_headers)
    vid = _create_visit(client, pid, doctor_headers)

    file_tuple = ("script.exe", io.BytesIO(b"malicious code"), "application/x-msdownload")
    resp = client.post(
        f"/api/visits/{vid}/labs",
        data={"test_name": "Malicious Upload"},
        files={"file": file_tuple},
        headers=doctor_headers,
    )
    assert resp.status_code == 400
    assert "not allowed" in resp.json()["detail"]


def test_list_labs_and_visit_detail_aggregation(client, doctor_headers):
    pid = _create_patient(client, doctor_headers)
    vid = _create_visit(client, pid, doctor_headers)

    client.post(
        f"/api/visits/{vid}/labs",
        data={"category": "ecg", "test_name": "12-Lead ECG", "result_summary": "Normal sinus rhythm"},
        headers=doctor_headers,
    )

    # List labs
    resp = client.get(f"/api/visits/{vid}/labs", headers=doctor_headers)
    assert resp.status_code == 200
    labs = resp.json()
    assert len(labs) >= 1
    assert labs[0]["test_name"] == "12-Lead ECG"

    # Visit detail
    detail_resp = client.get(f"/api/visits/{vid}", headers=doctor_headers)
    assert detail_resp.status_code == 200
    visit_detail = detail_resp.json()
    assert "labs" in visit_detail
    assert len(visit_detail["labs"]) >= 1
    assert visit_detail["labs"][0]["test_name"] == "12-Lead ECG"


def test_delete_lab_result(client, doctor_headers):
    pid = _create_patient(client, doctor_headers)
    vid = _create_visit(client, pid, doctor_headers)

    fake_file_content = b"ECG trace data"
    file_tuple = ("ecg.txt", io.BytesIO(fake_file_content), "text/plain")

    create_resp = client.post(
        f"/api/visits/{vid}/labs",
        data={"category": "ecg", "test_name": "Temporary ECG"},
        files={"file": file_tuple},
        headers=doctor_headers,
    )
    lab_id = create_resp.json()["id"]
    file_url = create_resp.json()["file_url"]

    # Delete lab
    del_resp = client.delete(f"/api/labs/{lab_id}", headers=doctor_headers)
    assert del_resp.status_code == 204

    # Verify deleted from list
    list_resp = client.get(f"/api/visits/{vid}/labs", headers=doctor_headers)
    assert not any(item["id"] == lab_id for item in list_resp.json())


def test_lab_rbac(client, readonly_headers, doctor_headers):
    pid = _create_patient(client, doctor_headers)
    vid = _create_visit(client, pid, doctor_headers)

    # Read-only user cannot upload labs
    resp = client.post(
        f"/api/visits/{vid}/labs",
        data={"test_name": "Forbidden Test"},
        headers=readonly_headers,
    )
    assert resp.status_code == 403

    # Read-only user CAN view labs
    list_resp = client.get(f"/api/visits/{vid}/labs", headers=readonly_headers)
    assert list_resp.status_code == 200
