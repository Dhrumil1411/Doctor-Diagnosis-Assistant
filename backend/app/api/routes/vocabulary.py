from fastapi import APIRouter, Depends

from app.api.deps import require_reader
from app.services.classifier import ClassifierService, get_classifier

router = APIRouter(tags=["vocabulary"])


@router.get("/api/symptom-vocabulary")
def symptom_vocabulary(
    classifier: ClassifierService = Depends(get_classifier),
    user=Depends(require_reader),
) -> list[dict]:
    return classifier.vocabulary()
