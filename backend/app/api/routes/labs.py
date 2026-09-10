import os
import uuid
from datetime import datetime
from pathlib import Path

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    UploadFile,
    status,
)
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import require_reader, require_writer
from app.db.base import get_db
from app.models.lab_results import LabCategory, LabResult
from app.models.visits import Visit
from app.schemas.lab_result import LabResultRead
from app.services.audit import record_audit

router = APIRouter(tags=["labs"])


def _get_visit_or_404(db: Session, visit_id: uuid.UUID) -> Visit:
    visit = db.get(Visit, visit_id)
    if visit is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Visit not found"
        )
    return visit

UPLOAD_DIR = Path("uploads/labs")
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB
ALLOWED_EXTENSIONS = {
    ".pdf", ".png", ".jpg", ".jpeg", ".gif", ".webp",
    ".txt", ".csv", ".doc", ".docx", ".dcm", ".dicom",
}


def _get_lab_or_404(db: Session, lab_id: uuid.UUID) -> LabResult:
    lab = db.get(LabResult, lab_id)
    if lab is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Lab result not found"
        )
    return lab


def _to_read_schema(lab: LabResult) -> LabResultRead:
    file_url = None
    if lab.file_path:
        # Convert local path to web static URL
        filename = Path(lab.file_path).name
        file_url = f"/uploads/labs/{filename}"
    return LabResultRead(
        id=lab.id,
        visit_id=lab.visit_id,
        category=lab.category,
        test_name=lab.test_name,
        result_summary=lab.result_summary,
        file_path=lab.file_path,
        file_url=file_url,
        performed_at=lab.performed_at,
    )


@router.post("/api/visits/{visit_id}/labs", response_model=LabResultRead, status_code=status.HTTP_201_CREATED)
async def create_lab_result(
    visit_id: uuid.UUID,
    category: LabCategory = Form(LabCategory.other),
    test_name: str = Form(...),
    result_summary: str | None = Form(None),
    performed_at: str | None = Form(None),
    file: UploadFile | None = File(None),
    db: Session = Depends(get_db),
    user=Depends(require_writer),
) -> LabResultRead:
    visit = _get_visit_or_404(db, visit_id)

    parsed_performed_at = None
    if performed_at and performed_at.strip():
        try:
            parsed_performed_at = datetime.fromisoformat(performed_at.strip())
        except ValueError:
            pass

    saved_file_path = None
    if file and file.filename:
        ext = Path(file.filename).suffix.lower()
        if ext not in ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File extension '{ext}' is not allowed. Allowed: {', '.join(sorted(ALLOWED_EXTENSIONS))}",
            )
        
        # Read content and check size limit
        contents = await file.read()
        if len(contents) > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File size exceeds 10 MB limit ({len(contents)} bytes)",
            )

        # Create target directory
        target_dir = UPLOAD_DIR
        target_dir.mkdir(parents=True, exist_ok=True)

        safe_filename = f"{uuid.uuid4().hex}_{Path(file.filename).name}"
        full_path = target_dir / safe_filename
        with open(full_path, "wb") as f:
            f.write(contents)
        saved_file_path = str(full_path)

    lab = LabResult(
        visit_id=visit.id,
        category=category,
        test_name=test_name,
        result_summary=result_summary,
        file_path=saved_file_path,
        performed_at=parsed_performed_at,
    )
    db.add(lab)
    db.commit()
    db.refresh(lab)

    record_audit(
        db,
        actor_user_id=user.id,
        action="create_lab",
        entity_type="lab_result",
        entity_id=lab.id,
        detail={"test_name": test_name, "category": category.value, "has_file": bool(saved_file_path)},
    )
    db.commit()

    return _to_read_schema(lab)


@router.get("/api/visits/{visit_id}/labs", response_model=list[LabResultRead])
def list_lab_results(
    visit_id: uuid.UUID,
    db: Session = Depends(get_db),
    user=Depends(require_reader),
) -> list[LabResultRead]:
    _get_visit_or_404(db, visit_id)
    labs = list(
        db.scalars(
            select(LabResult)
            .where(LabResult.visit_id == visit_id)
            .order_by(LabResult.id.asc())
        ).all()
    )
    return [_to_read_schema(lab) for lab in labs]


@router.delete("/api/labs/{lab_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_lab_result(
    lab_id: uuid.UUID,
    db: Session = Depends(get_db),
    user=Depends(require_writer),
) -> None:
    lab = _get_lab_or_404(db, lab_id)
    if lab.file_path and os.path.exists(lab.file_path):
        try:
            os.remove(lab.file_path)
        except OSError:
            pass

    record_audit(
        db,
        actor_user_id=user.id,
        action="delete_lab",
        entity_type="lab_result",
        entity_id=lab.id,
        detail={"test_name": lab.test_name},
    )
    db.delete(lab)
    db.commit()
