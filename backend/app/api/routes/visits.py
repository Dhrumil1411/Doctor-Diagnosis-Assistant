import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import require_reader, require_writer
from app.api.routes.patients import _get_patient_or_404
from app.db.base import get_db
from app.models.general_exam import GeneralExam
from app.models.lab_results import LabResult
from app.models.social_history import SocialHistory
from app.models.symptoms import Symptom
from app.models.visits import Visit
from app.models.vitals import Vitals
from app.api.routes.labs import _to_read_schema
from app.schemas.visit import (
    GeneralExamRead,
    GeneralExamUpsert,
    SocialHistoryRead,
    SocialHistoryUpsert,
    SymptomEntryCreate,
    SymptomEntryRead,
    VitalsRead,
    VitalsUpsert,
    VisitCreate,
    VisitDetail,
    VisitRead,
    VisitUpdate,
)
from app.services.audit import record_audit

router = APIRouter(tags=["visits"])


def _get_visit_or_404(db: Session, visit_id: uuid.UUID) -> Visit:
    visit = db.get(Visit, visit_id)
    if visit is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Visit not found"
        )
    return visit


@router.post("/api/visits", response_model=VisitRead,
             status_code=status.HTTP_201_CREATED)
def create_visit(
    payload: VisitCreate,
    db: Session = Depends(get_db),
    user=Depends(require_writer),
) -> Visit:
    _get_patient_or_404(db, payload.patient_id)
    visit = Visit(**payload.model_dump(exclude={"patient_id"}), patient_id=payload.patient_id)
    db.add(visit)
    record_audit(db, actor_user_id=user.id, action="create",
                 entity_type="visit", entity_id=visit.id)
    db.commit()
    db.refresh(visit)
    return visit


@router.get("/api/patients/{patient_id}/visits", response_model=list[VisitRead])
def list_visits_for_patient(
    patient_id: uuid.UUID,
    db: Session = Depends(get_db),
    user=Depends(require_reader),
) -> list[Visit]:
    _get_patient_or_404(db, patient_id)
    return list(db.scalars(
        select(Visit).where(Visit.patient_id == patient_id).order_by(Visit.occurred_at.desc())
    ).all())


@router.get("/api/visits/{visit_id}", response_model=VisitDetail)
def get_visit(
    visit_id: uuid.UUID,
    db: Session = Depends(get_db),
    user=Depends(require_reader),
) -> VisitDetail:
    visit = _get_visit_or_404(db, visit_id)
    detail = VisitDetail.model_validate(visit)
    detail.symptoms = list(db.scalars(
        select(Symptom).where(Symptom.visit_id == visit.id)
    ).all())
    detail.vitals = db.scalar(select(Vitals).where(Vitals.visit_id == visit.id))
    detail.social_history = db.scalar(
        select(SocialHistory).where(SocialHistory.visit_id == visit.id))
    detail.general_exam = db.scalar(
        select(GeneralExam).where(GeneralExam.visit_id == visit.id))
    labs = list(db.scalars(
        select(LabResult).where(LabResult.visit_id == visit.id).order_by(LabResult.id.asc())
    ).all())
    detail.labs = [_to_read_schema(lab) for lab in labs]
    return detail


@router.patch("/api/visits/{visit_id}", response_model=VisitRead)
def update_visit(
    visit_id: uuid.UUID,
    payload: VisitUpdate,
    db: Session = Depends(get_db),
    user=Depends(require_writer),
) -> Visit:
    visit = _get_visit_or_404(db, visit_id)
    changes = payload.model_dump(exclude_unset=True)
    for field, value in changes.items():
        setattr(visit, field, value)
    record_audit(db, actor_user_id=user.id, action="update",
                 entity_type="visit", entity_id=visit.id, detail=changes)
    db.commit()
    db.refresh(visit)
    return visit


@router.put("/api/visits/{visit_id}/symptoms", response_model=list[SymptomEntryRead])
def replace_symptoms(
    visit_id: uuid.UUID,
    entries: list[SymptomEntryCreate],
    db: Session = Depends(get_db),
    user=Depends(require_writer),
) -> list[Symptom]:
    visit = _get_visit_or_404(db, visit_id)
    for existing in db.scalars(select(Symptom).where(Symptom.visit_id == visit.id)).all():
        db.delete(existing)
    items = [Symptom(**entry.model_dump(), visit_id=visit.id) for entry in entries]
    db.add_all(items)
    record_audit(db, actor_user_id=user.id, action="replace_symptoms",
                 entity_type="visit", entity_id=visit.id,
                 detail={"count": len(items)})
    db.commit()
    return items


@router.put("/api/visits/{visit_id}/vitals", response_model=VitalsRead)
def upsert_vitals(
    visit_id: uuid.UUID,
    payload: VitalsUpsert,
    db: Session = Depends(get_db),
    user=Depends(require_writer),
) -> Vitals:
    visit = _get_visit_or_404(db, visit_id)
    vitals = db.scalar(select(Vitals).where(Vitals.visit_id == visit.id))
    changes = payload.model_dump(exclude_unset=True)
    if vitals is None:
        vitals = Vitals(**changes, visit_id=visit.id)
        db.add(vitals)
        audited_action = "create"
    else:
        for field, value in changes.items():
            setattr(vitals, field, value)
        audited_action = "update"
    record_audit(db, actor_user_id=user.id, action=audited_action,
                 entity_type="vitals", entity_id=vitals.id)
    db.commit()
    db.refresh(vitals)
    return vitals


@router.put("/api/visits/{visit_id}/social-history", response_model=SocialHistoryRead)
def upsert_social_history(
    visit_id: uuid.UUID,
    payload: SocialHistoryUpsert,
    db: Session = Depends(get_db),
    user=Depends(require_writer),
) -> SocialHistory:
    visit = _get_visit_or_404(db, visit_id)
    social = db.scalar(select(SocialHistory).where(SocialHistory.visit_id == visit.id))
    changes = payload.model_dump(exclude_unset=True)
    if social is None:
        social = SocialHistory(**changes, visit_id=visit.id)
        db.add(social)
        audited_action = "create"
    else:
        for field, value in changes.items():
            setattr(social, field, value)
        audited_action = "update"
    record_audit(db, actor_user_id=user.id, action=audited_action,
                 entity_type="social_history", entity_id=social.id)
    db.commit()
    db.refresh(social)
    return social


@router.put("/api/visits/{visit_id}/general-exam", response_model=GeneralExamRead)
def upsert_general_exam(
    visit_id: uuid.UUID,
    payload: GeneralExamUpsert,
    db: Session = Depends(get_db),
    user=Depends(require_writer),
) -> GeneralExam:
    visit = _get_visit_or_404(db, visit_id)
    exam = db.scalar(select(GeneralExam).where(GeneralExam.visit_id == visit.id))
    changes = payload.model_dump(exclude_unset=True)
    if exam is None:
        exam = GeneralExam(**changes, visit_id=visit.id)
        db.add(exam)
        audited_action = "create"
    else:
        for field, value in changes.items():
            setattr(exam, field, value)
        audited_action = "update"
    record_audit(db, actor_user_id=user.id, action=audited_action,
                 entity_type="general_exam", entity_id=exam.id)
    db.commit()
    db.refresh(exam)
    return exam
