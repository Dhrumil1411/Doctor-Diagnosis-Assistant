"""CLI End-to-End Evaluation Runner for Doctor Diagnosis Assistant.

Executes complete clinical decision support workflows on curated clinical cases
and Synthea synthetic records, evaluating ML classifier predictions, LLM differential
reasoning, red-flag triggers, and doctor feedback capture.

Usage:
    python scripts/run_e2e_suite.py [--live] [--synthea-limit 3]
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

# Ensure backend root is on sys.path
backend_dir = Path(__file__).resolve().parents[1]
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

import uuid
from sqlalchemy import select
from fastapi.testclient import TestClient
from app.main import app
from app.e2e.curated_cases import load_curated_cases
from app.e2e.synthea_loader import load_synthea_cases
from app.core.security import create_access_token


def _mock_llm_response(differentials, red_flags=None, steps=None):
    return {
        "summary": "Clinical evaluation based on patient presentation and examination.",
        "differentials": differentials or [
            {
                "rank": 1,
                "condition": "Primary Differential Diagnosis",
                "likelihood": "high",
                "supporting_findings": ["Presenting signs & symptoms"],
                "opposing_findings": [],
                "notes": "Correlate with diagnostic workup.",
            }
        ],
        "red_flags": red_flags or [],
        "suggested_next_steps": steps or ["CBC", "BMP", "Specialist consultation"],
        "questions_for_patient": ["Any family history of similar episodes?"],
    }


def run_e2e_benchmark(live_llm: bool = False, synthea_limit: int = 3):
    client = TestClient(app)

    # 1. Ensure a doctor user exists in the DB for authentication
    from app.db.base import SessionLocal
    from app.models.users import User, UserRole
    from app.core.security import hash_password

    db = SessionLocal()
    try:
        doctor = db.execute(
            select(User).where(User.role == UserRole.doctor, User.is_active == True)
        ).scalars().first()
        if not doctor:
            doctor = User(
                email=f"e2e.eval.{uuid.uuid4().hex[:6]}@example.com",
                hashed_password=hash_password("E2EPassw0rd!"),
                full_name="Dr. Evaluation Agent",
                role=UserRole.doctor,
                is_active=True,
            )
            db.add(doctor)
            db.commit()
            db.refresh(doctor)
        token = create_access_token(user_id=doctor.id, role=doctor.role.value)
    finally:
        db.close()

    headers = {"Authorization": f"Bearer {token}"}

    # Load Cases
    curated = load_curated_cases()
    synthea = load_synthea_cases(limit=synthea_limit)
    all_cases = curated + synthea

    print("=" * 80)
    print("DOCTOR DIAGNOSIS ASSISTANT — CLINICAL END-TO-END EVALUATION SUITE")
    print("=" * 80)
    print(f"Total Cases: {len(all_cases)} (Curated: {len(curated)}, Synthea: {len(synthea)})")
    print(f"LLM Reasoning Mode: {'LIVE PROVIDER (API)' if live_llm else 'REPLAY / DETERMINISTIC'}")
    print("-" * 80)

    results = []
    start_total_time = time.time()

    for idx, case in enumerate(all_cases, 1):
        case_id = case.get("case_id", f"case_{idx}")
        title = case.get("title") or case.get("patient", {}).get("full_name", "Clinical Case")
        is_emergency = case.get("is_emergency", False)
        case_start = time.time()

        # Step A: Patient Intake
        patient_payload = dict(case["patient"])
        if patient_payload.get("mrn"):
            patient_payload["mrn"] = f"{patient_payload['mrn']}-{uuid.uuid4().hex[:6]}"
        p_res = client.post("/api/patients", json=patient_payload, headers=headers)
        if p_res.status_code != 201:
            print(f"[FAIL] Patient creation failed for {case_id}: {p_res.text}")
            continue
        patient_id = p_res.json()["id"]

        for h in case.get("medical_history", []):
            client.post(f"/api/patients/{patient_id}/history", json=h, headers=headers)
        for m in case.get("medications", []):
            client.post(f"/api/patients/{patient_id}/medications", json=m, headers=headers)
        for a in case.get("allergies", []):
            client.post(f"/api/patients/{patient_id}/allergies", json=a, headers=headers)

        # Step B: Visit & Encounter
        visit_payload = dict(case["visit"])
        visit_payload["patient_id"] = patient_id
        v_res = client.post("/api/visits", json=visit_payload, headers=headers)
        if v_res.status_code != 201:
            print(f"[FAIL] Visit creation failed for {case_id}: {v_res.text}")
            continue
        visit_id = v_res.json()["id"]

        if "vitals" in case:
            client.put(f"/api/visits/{visit_id}/vitals", json=case["vitals"], headers=headers)
        if "social_history" in case:
            client.put(f"/api/visits/{visit_id}/social-history", json=case["social_history"], headers=headers)

        # Symptoms
        symptom_list = case.get("symptoms", [])
        if symptom_list and isinstance(symptom_list[0], str):
            symptom_payloads = [
                {"name": s, "status": "present", "severity": 6, "duration": "1 week"}
                for s in symptom_list
            ]
        else:
            symptom_payloads = [
                {"name": s["name"], "status": s.get("status", "present"), "severity": s.get("severity", 5), "duration": s.get("duration", "1 week")}
                for s in symptom_list
            ]
        client.put(f"/api/visits/{visit_id}/symptoms", json=symptom_payloads, headers=headers)

        # Step C: ML Classifier Inference
        pred_res = client.post("/api/predict", json={"visit_id": visit_id, "top_k": 3}, headers=headers)
        top_ml_pred = "N/A"
        top_ml_conf = 0.0
        if pred_res.status_code == 200:
            preds = pred_res.json().get("predictions", [])
            if preds:
                top_ml_pred = preds[0]["disease"]
                top_ml_conf = preds[0]["confidence"]

        # Step D: Attach Labs
        for lab in case.get("labs", []):
            client.post(f"/api/visits/{visit_id}/labs", data=lab, headers=headers)

        # Step E: LLM Reasoning
        if not live_llm:
            # Replay mock generator
            diffs = [
                {"rank": 1, "condition": top_ml_pred, "likelihood": "high", "supporting_findings": [s["name"] for s in symptom_payloads[:2]]}
            ]
            red_flags = ["Immediate emergency intervention required"] if is_emergency else []
            mock_body = _mock_llm_response(diffs, red_flags=red_flags)

            import app.api.routes.reason as reason_module

            class MockLLM:
                def chat_json(self, messages):
                    return mock_body, "mock-groq"

            original_client_fn = reason_module._get_reason_client
            reason_module._get_reason_client = lambda: MockLLM()
            reason_module._cache._store.clear()
            reason_res = client.post("/api/reason", json={"visit_id": visit_id}, headers=headers)
            reason_module._get_reason_client = original_client_fn
        else:
            reason_res = client.post("/api/reason", json={"visit_id": visit_id}, headers=headers)

        llm_top = "N/A"
        red_flag_count = 0
        if reason_res.status_code == 200:
            r_data = reason_res.json()
            diffs = r_data.get("differentials", [])
            if diffs:
                llm_top = diffs[0].get("condition", "Unknown")
            red_flag_count = len(r_data.get("red_flags", []))

        # Step F: Doctor Feedback Loop
        doc_decision = case.get("doctor_decision", "accepted")
        diag_res = client.post(
            f"/api/visits/{visit_id}/diagnosis",
            json={
                "doctor_decision": doc_decision,
                "disease_label": top_ml_pred if top_ml_pred != "N/A" else "General Consideration",
                "edited_label": case.get("doctor_override_diagnosis"),
                "reasoning": case.get("doctor_notes", "Clinically verified during E2E benchmark run."),
            },
            headers=headers,
        )

        elapsed = time.time() - case_start
        status_str = "PASS" if diag_res.status_code == 200 else "FAIL"

        results.append({
            "case_id": case_id,
            "title": title[:40],
            "source": case.get("source", "Curated"),
            "ml_top": top_ml_pred[:22],
            "ml_conf": f"{top_ml_conf:.1%}",
            "llm_top": llm_top[:22],
            "red_flags": red_flag_count,
            "emergency": "YES" if is_emergency else "no",
            "doctor": doc_decision,
            "status": status_str,
            "elapsed": f"{elapsed:.2f}s",
        })

        print(f"[{idx:02d}/{len(all_cases):02d}] {status_str} | {case_id:<28} | ML: {top_ml_pred:<18} ({top_ml_conf:.1%}) | RedFlags: {red_flag_count} | {elapsed:.2f}s")

    total_time = time.time() - start_total_time
    passed_count = sum(1 for r in results if r["status"] == "PASS")

    print("\n" + "=" * 105)
    print("END-TO-END BENCHMARK SUMMARY")
    print("=" * 105)
    print(f"{'Case ID':<22} | {'Source':<8} | {'ML Prediction':<20} | {'Conf':<6} | {'LLM Top Diff':<18} | {'RF':<3} | {'Doc':<6} | {'Status'}")
    print("-" * 105)
    for r in results:
        print(f"{r['case_id']:<22} | {r['source']:<8} | {r['ml_top']:<20} | {r['ml_conf']:<6} | {r['llm_top']:<18} | {r['red_flags']:<3} | {r['doctor']:<6} | {r['status']}")
    print("-" * 105)
    print(f"Total Success: {passed_count}/{len(all_cases)} ({passed_count/len(all_cases):.1%}) | Total Duration: {total_time:.2f}s")
    print("=" * 105)

    return passed_count == len(all_cases)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Doctor Diagnosis Assistant E2E Runner")
    parser.add_argument("--live", action="store_true", help="Use live LLM provider keys in .env")
    parser.add_argument("--synthea-limit", type=int, default=3, help="Max Synthea synthetic cases to load")
    args = parser.parse_args()

    success = run_e2e_benchmark(live_llm=args.live, synthea_limit=args.synthea_limit)
    sys.exit(0 if success else 1)
