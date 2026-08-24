from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import require_writer
from app.db.base import get_db
from app.models.symptoms import Symptom, SymptomStatus
from app.models.visits import Visit
from app.schemas.prediction import PredictRequest, PredictResponse
from app.services.audit import record_audit
from app.services.classifier import ClassifierService, get_classifier

router = APIRouter(tags=["predict"])


def _symptoms_for_visit(db: Session, visit_id) -> tuple[Visit, list[str]]:
    visit = db.get(Visit, visit_id)
    if visit is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Visit not found"
        )
    rows = db.scalars(
        select(Symptom.name).where(
            Symptom.visit_id == visit.id, Symptom.status == SymptomStatus.present
        )
    ).all()
    return visit, [str(r) for r in rows]


@router.post("/api/predict", response_model=PredictResponse)
def predict(
    payload: PredictRequest,
    db: Session = Depends(get_db),
    user=Depends(require_writer),
    classifier: ClassifierService = Depends(get_classifier),
) -> PredictResponse:
    if payload.visit_id is not None:
        _visit, symptom_ids = _symptoms_for_visit(db, payload.visit_id)
        if not symptom_ids:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Visit has no symptoms with status 'present'",
            )
    else:
        symptom_ids = [s for s in (payload.symptoms or [])]

    result = classifier.predict(symptom_ids, top_k=payload.top_k)
    record_audit(
        db,
        actor_user_id=user.id,
        action="predict",
        entity_type="visit" if payload.visit_id else "ad_hoc",
        entity_id=payload.visit_id,
        detail={
            "n_symptoms": len(result["recognized_symptoms"]),
            "top": result["predictions"][0]["disease"],
        },
    )
    db.commit()
    return PredictResponse(model_name=classifier.model_name, **result)
