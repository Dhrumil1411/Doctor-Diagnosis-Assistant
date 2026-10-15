import uuid
from typing import Any
from pydantic import BaseModel, ConfigDict


class AuditLogRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    actor_user_id: uuid.UUID | None = None
    actor_email: str | None = None
    actor_name: str | None = None
    action: str
    entity_type: str
    entity_id: uuid.UUID | None = None
    detail: dict[str, Any] | None = None
    ip_address: str | None = None


class AuditLogPage(BaseModel):
    items: list[AuditLogRead]
    total: int
    limit: int
    offset: int
