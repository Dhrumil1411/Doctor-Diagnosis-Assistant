import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.lab_results import LabCategory


class LabResultCreate(BaseModel):
    category: LabCategory = LabCategory.other
    test_name: str = Field(min_length=1, max_length=200)
    result_summary: str | None = None
    performed_at: datetime | None = None


class LabResultRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    visit_id: uuid.UUID
    category: LabCategory
    test_name: str
    result_summary: str | None = None
    file_path: str | None = None
    file_url: str | None = None
    performed_at: datetime | None = None
