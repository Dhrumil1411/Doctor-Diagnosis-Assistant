import json

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import require_writer
from app.db.base import get_db
from app.schemas.prediction import Prediction
from app.schemas.reason import Differential, ReasonRequest, ReasonResponse
from app.services.audit import record_audit
from app.services.case import assemble_case
from app.services.classifier import ClassifierService, get_classifier
from app.services.llm import LLMClient, LLMError, ReasonCache
from app.services.prompts import SYSTEM_PROMPT

router = APIRouter(tags=["reason"])

_cache = ReasonCache()


def _get_reason_client() -> LLMClient:
    from app.core.config import get_settings

    return LLMClient(get_settings())


def _classifier_block(
    classifier: ClassifierService, symptom_names: list[str]
) -> list[Prediction] | None:
    if not symptom_names:
        return None
    result = classifier.predict(symptom_names, top_k=3)
    return [Prediction(**p) for p in result["predictions"]]


@router.post("/api/reason", response_model=ReasonResponse)
def reason(
    payload: ReasonRequest,
    db: Session = Depends(get_db),
    user=Depends(require_writer),
    classifier: ClassifierService = Depends(get_classifier),
) -> ReasonResponse:
    try:
        case = assemble_case(db, payload.visit_id)
    except LookupError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc

    if not case["symptoms_present"]:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Visit has no symptoms with status 'present'",
        )

    classifier_predictions: list[Prediction] = []
    if payload.include_classifier:
        names = [s["name"] for s in case["symptoms_present"]]
        block = _classifier_block(classifier, names)
        if block is not None:
            classifier_predictions = block

    cache_payload = {"case": case, "classifier": [p.model_dump() for p in classifier_predictions]}
    cache_key = _cache.make_key(cache_payload)

    if not payload.force_refresh:
        cached = _cache.get(cache_key)
        if cached is not None:
            record_audit(
                db, actor_user_id=user.id, action="reason_cached",
                entity_type="visit", entity_id=payload.visit_id,
            )
            db.commit()
            return ReasonResponse(visit_id=payload.visit_id, cached=True, **cached)

    llm_messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "user",
            "content": json.dumps(case, default=str, ensure_ascii=False)
            + "\n\nBaseline ML classifier (fast cross-check only, may be wrong):\n"
            + json.dumps([p.model_dump() for p in classifier_predictions]),
        },
    ]
    client = _get_reason_client()
    try:
        parsed, provider_name = client.chat_json(llm_messages)
    except LLMError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)
        ) from exc

    differentials = []
    for entry in parsed.get("differentials", []):
        try:
            differentials.append(Differential(**entry))
        except Exception:
            continue
    if not differentials:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="LLM returned no usable differentials",
        )

    response_data = {
        "provider": provider_name,
        "model": _model_name(provider_name),
        "summary": parsed.get("summary"),
        "differentials": [d.model_dump() for d in differentials],
        "red_flags": _string_list(parsed.get("red_flags")),
        "suggested_next_steps": _string_list(parsed.get("suggested_next_steps")),
        "questions_for_patient": _string_list(parsed.get("questions_for_patient")),
        "classifier_predictions": [p.model_dump() for p in classifier_predictions],
    }
    _cache.put(cache_key, response_data)

    record_audit(
        db, actor_user_id=user.id, action="reason",
        entity_type="visit", entity_id=payload.visit_id,
        detail={"provider": provider_name, "top": differentials[0].condition},
    )
    db.commit()
    return ReasonResponse(visit_id=payload.visit_id, cached=False, **response_data)


def _model_name(provider: str) -> str:
    from app.core.config import get_settings

    s = get_settings()
    return s.groq_model if provider == "groq" else s.openrouter_model


def _string_list(value) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(v) for v in value if v is not None and str(v).strip()]
