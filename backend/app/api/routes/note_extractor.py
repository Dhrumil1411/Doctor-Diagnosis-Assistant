import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import require_writer
from app.core.config import Settings, get_settings
from app.db.base import get_db
from app.schemas.note_extractor import ExtractNoteRequest, ExtractedClinicalCase
from app.services.audit import record_audit
from app.services.note_extractor import extract_clinical_note

router = APIRouter(tags=["clinical-notes"])
logger = logging.getLogger("uvicorn.error")


@router.post("/api/clinical-notes/extract", response_model=ExtractedClinicalCase)
def extract_note(
    payload: ExtractNoteRequest,
    db: Session = Depends(get_db),
    user=Depends(require_writer),
    settings: Settings = Depends(get_settings),
) -> ExtractedClinicalCase:
    """Extract structured clinical case entities, HPO symptoms, vitals, and history from raw text notes."""
    try:
        extracted = extract_clinical_note(payload.raw_note, settings)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        logger.error("Failed to extract clinical note: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Clinical note extraction failed: {exc}",
        ) from exc

    record_audit(
        db,
        actor_user_id=user.id,
        action="clinical_note_extracted",
        entity_type="clinical_note",
        entity_id=None,
    )
    db.commit()

    return extracted
