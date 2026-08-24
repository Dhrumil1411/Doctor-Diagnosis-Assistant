import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import require_reader, require_writer
from app.db.base import get_db
from app.models.allergies import Allergy
from app.models.medical_history import MedicalHistory
from app.models.medications import Medication
from app.models.patients import Patient
from app.schemas.clinical import (
    AllergyCreate,
    AllergyRead,
    AllergyUpdate,
    HistoryEntryCreate,
    HistoryEntryRead,
    HistoryEntryUpdate,
    MedicationCreate,
    MedicationRead,
    MedicationUpdate,
)
from app.schemas.patient import PatientCreate, PatientDetail, PatientRead, PatientUpdate
from app.services.audit import record_audit

router = APIRouter(prefix="/api/patients", tags=["patients"])


def _get_patient_or_404(db: Session, patient_id: uuid.UUID) -> Patient:
    patient = db.get(Patient, patient_id)
    if patient is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found"
        )
    return patient


def _check_mrn_free(db: Session, mrn: str | None, exclude_id: uuid.UUID | None = None):
    if mrn is None:
        return
    stmt = select(Patient).where(Patient.mrn == mrn)
    if exclude_id is not None:
        stmt = stmt.where(Patient.id != exclude_id)
    if db.scalar(stmt):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="MRN already in use"
        )


@router.post("", response_model=PatientRead, status_code=status.HTTP_201_CREATED)
def create_patient(
    payload: PatientCreate,
    db: Session = Depends(get_db),
    user=Depends(require_writer),
) -> Patient:
    _check_mrn_free(db, payload.mrn)
    patient = Patient(**payload.model_dump(), created_by_id=user.id)
    db.add(patient)
    record_audit(db, actor_user_id=user.id, action="create",
                 entity_type="patient", entity_id=patient.id)
    db.commit()
    db.refresh(patient)
    return patient


@router.get("", response_model=list[PatientRead])
def list_patients(
    q: str | None = Query(default=None, max_length=255),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    user=Depends(require_reader),
) -> list[Patient]:
    stmt = select(Patient).order_by(Patient.created_at.desc())
    if q:
        like = f"%{q}%"
        stmt = stmt.where(Patient.full_name.ilike(like) | Patient.mrn.ilike(like))
    return list(db.scalars(stmt.limit(limit).offset(offset)).all())


@router.get("/{patient_id}", response_model=PatientDetail)
def get_patient(
    patient_id: uuid.UUID,
    db: Session = Depends(get_db),
    user=Depends(require_reader),
) -> PatientDetail:
    patient = _get_patient_or_404(db, patient_id)
    detail = PatientDetail.model_validate(patient)
    detail.allergies = list(db.scalars(
        select(Allergy).where(Allergy.patient_id == patient.id)
    ).all())
    detail.history = list(db.scalars(
        select(MedicalHistory).where(MedicalHistory.patient_id == patient.id)
    ).all())
    detail.medications = list(db.scalars(
        select(Medication).where(Medication.patient_id == patient.id)
    ).all())
    return detail


@router.patch("/{patient_id}", response_model=PatientRead)
def update_patient(
    patient_id: uuid.UUID,
    payload: PatientUpdate,
    db: Session = Depends(get_db),
    user=Depends(require_writer),
) -> Patient:
    patient = _get_patient_or_404(db, patient_id)
    changes = payload.model_dump(exclude_unset=True)
    if "mrn" in changes:
        _check_mrn_free(db, changes["mrn"], exclude_id=patient.id)
    for field, value in changes.items():
        setattr(patient, field, value)
    record_audit(db, actor_user_id=user.id, action="update",
                 entity_type="patient", entity_id=patient.id, detail=changes)
    db.commit()
    db.refresh(patient)
    return patient


def _child_route(entity_model, create_schema, update_schema, read_schema,
                 entity_name: str, path_segment: str):
    child = APIRouter()

    def _get_child_or_404(db: Session, patient_id: uuid.UUID, item_id: uuid.UUID):
        item = db.get(entity_model, item_id)
        if item is None or item.patient_id != patient_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"{entity_name} not found for this patient",
            )
        return item

    @child.get("/{patient_id}/" + path_segment, response_model=list[read_schema])
    def list_children(
        patient_id: uuid.UUID,
        db: Session = Depends(get_db),
        user=Depends(require_reader),
    ):
        _get_patient_or_404(db, patient_id)
        return list(db.scalars(
            select(entity_model).where(entity_model.patient_id == patient_id)
        ).all())

    @child.post(
        "/{patient_id}/" + path_segment,
        response_model=read_schema,
        status_code=status.HTTP_201_CREATED,
    )
    def create_child(
        patient_id: uuid.UUID,
        payload: create_schema,
        db: Session = Depends(get_db),
        user=Depends(require_writer),
    ):
        _get_patient_or_404(db, patient_id)
        item = entity_model(**payload.model_dump(), patient_id=patient_id)
        db.add(item)
        record_audit(db, actor_user_id=user.id, action="create",
                     entity_type=entity_name, entity_id=item.id)
        db.commit()
        db.refresh(item)
        return item

    @child.patch(
        "/{patient_id}/" + path_segment + "/{item_id}",
        response_model=read_schema,
    )
    def update_child(
        patient_id: uuid.UUID,
        item_id: uuid.UUID,
        payload: update_schema,
        db: Session = Depends(get_db),
        user=Depends(require_writer),
    ):
        item = _get_child_or_404(db, patient_id, item_id)
        changes = payload.model_dump(exclude_unset=True)
        for field, value in changes.items():
            setattr(item, field, value)
        record_audit(db, actor_user_id=user.id, action="update",
                     entity_type=entity_name, entity_id=item.id, detail=changes)
        db.commit()
        db.refresh(item)
        return item

    @child.delete(
        "/{patient_id}/" + path_segment + "/{item_id}",
        status_code=status.HTTP_204_NO_CONTENT,
    )
    def delete_child(
        patient_id: uuid.UUID,
        item_id: uuid.UUID,
        db: Session = Depends(get_db),
        user=Depends(require_writer),
    ):
        item = _get_child_or_404(db, patient_id, item_id)
        record_audit(db, actor_user_id=user.id, action="delete",
                     entity_type=entity_name, entity_id=item.id)
        db.delete(item)
        db.commit()

    return child


router.include_router(_child_route(Allergy, AllergyCreate, AllergyUpdate, AllergyRead, "allergy", "allergies"))
router.include_router(_child_route(MedicalHistory, HistoryEntryCreate, HistoryEntryUpdate, HistoryEntryRead, "history_entry", "history"))
router.include_router(_child_route(Medication, MedicationCreate, MedicationUpdate, MedicationRead, "medication", "medications"))
