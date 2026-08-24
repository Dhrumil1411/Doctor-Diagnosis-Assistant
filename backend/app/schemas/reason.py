import uuid

from pydantic import BaseModel, Field

from app.schemas.prediction import Prediction


class ReasonRequest(BaseModel):
    visit_id: uuid.UUID
    include_classifier: bool = True
    force_refresh: bool = False


class Differential(BaseModel):
    rank: int = Field(ge=1)
    condition: str
    likelihood: str | None = None
    supporting_findings: list[str] = []
    notes: str | None = None


class ReasonResponse(BaseModel):
    visit_id: uuid.UUID
    cached: bool
    provider: str
    model: str
    summary: str | None = None
    differentials: list[Differential] = []
    red_flags: list[str] = []
    suggested_next_steps: list[str] = []
    questions_for_patient: list[str] = []
    classifier_predictions: list[Prediction] = []
    disclaimer: str = (
        "Decision support only - not a substitute for clinical judgment. "
        "The doctor makes the final call."
    )
