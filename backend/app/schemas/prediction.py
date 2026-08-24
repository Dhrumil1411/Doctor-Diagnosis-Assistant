import uuid

from pydantic import BaseModel, Field, model_validator


class PredictRequest(BaseModel):
    symptoms: list[str] | None = Field(default=None, min_length=1, max_length=131)
    visit_id: uuid.UUID | None = None
    top_k: int = Field(default=5, ge=1, le=41)

    @model_validator(mode="after")
    def check_exactly_one_source(self) -> "PredictRequest":
        if (self.symptoms is None) == (self.visit_id is None):
            raise ValueError("provide exactly one of 'symptoms' or 'visit_id'")
        return self


class Prediction(BaseModel):
    rank: int
    disease: str
    confidence: float
    display_name: str | None = None


class PredictResponse(BaseModel):
    predictions: list[Prediction]
    recognized_symptoms: list[str]
    unknown_symptoms: list[str]
    model_name: str
