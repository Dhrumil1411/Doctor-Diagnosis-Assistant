import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import require_reader, require_writer
from app.api.routes.visits import _get_visit_or_404
from app.db.base import get_db
from app.models.diagnoses import Diagnosis
from app.schemas.diagnosis import DiagnosisDecisionCreate, DiagnosisRead
from app.services.audit import record_audit

router = APIRouter(tags=["diagnoses"])


@router.post("/api/visits/{visit_id}/diagnosis", response_model=DiagnosisRead)
def record_diagnosis_decision(
    visit_id: uuid.UUID,
    payload: DiagnosisDecisionCreate,
    db: Session = Depends(get_db),
    user=Depends(require_writer),
) -> Diagnosis:
    _get_visit_or_404(db, visit_id)

    # Check if existing diagnosis row exists for this visit
    existing = db.scalar(
        select(Diagnosis).where(Diagnosis.visit_id == visit_id)
    )

    if existing is None:
        existing = Diagnosis(
            visit_id=visit_id,
            source=payload.source,
            disease_label=payload.disease_label,
            edited_label=payload.edited_label,
            doctor_decision=payload.doctor_decision,
            confidence=payload.confidence,
            confidence_band=payload.confidence_band,
            reasoning=payload.reasoning,
            suggested_next_steps=payload.suggested_next_steps,
            decided_at=datetime.now(timezone.utc),
        )
        db.add(existing)
    else:
        existing.source = payload.source
        existing.disease_label = payload.disease_label
        existing.edited_label = payload.edited_label
        existing.doctor_decision = payload.doctor_decision
        if payload.confidence is not None:
            existing.confidence = payload.confidence
        if payload.confidence_band is not None:
            existing.confidence_band = payload.confidence_band
        if payload.reasoning is not None:
            existing.reasoning = payload.reasoning
        if payload.suggested_next_steps is not None:
            existing.suggested_next_steps = payload.suggested_next_steps
        existing.decided_at = datetime.now(timezone.utc)

    record_audit(
        db,
        actor_user_id=user.id,
        action="diagnosis_decision",
        entity_type="visit",
        entity_id=visit_id,
        detail={
            "decision": payload.doctor_decision.value,
            "disease_label": payload.disease_label,
            "edited_label": payload.edited_label,
        },
    )
    db.commit()
    db.refresh(existing)
    return existing


@router.get("/api/visits/{visit_id}/diagnosis", response_model=DiagnosisRead | None)
def get_diagnosis_decision(
    visit_id: uuid.UUID,
    db: Session = Depends(get_db),
    user=Depends(require_reader),
) -> Diagnosis | None:
    _get_visit_or_404(db, visit_id)
    return db.scalar(select(Diagnosis).where(Diagnosis.visit_id == visit_id))
