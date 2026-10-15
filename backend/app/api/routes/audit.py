import uuid
from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import require_admin
from app.db.base import get_db
from app.models.audit_log import AuditLog
from app.models.users import User
from app.schemas.audit import AuditLogPage, AuditLogRead

router = APIRouter(tags=["audit"])


@router.get("/api/audit-logs", response_model=AuditLogPage)
def list_audit_logs(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    action: str | None = Query(default=None),
    entity_type: str | None = Query(default=None),
    actor_user_id: uuid.UUID | None = Query(default=None),
    db: Session = Depends(get_db),
    admin=Depends(require_admin),
) -> AuditLogPage:
    """Retrieve paginated audit logs with optional filtering. Admin-only."""
    query = (
        select(
            AuditLog.id,
            AuditLog.actor_user_id,
            User.email.label("actor_email"),
            User.full_name.label("actor_name"),
            AuditLog.action,
            AuditLog.entity_type,
            AuditLog.entity_id,
            AuditLog.detail,
            AuditLog.ip_address,
        )
        .outerjoin(User, AuditLog.actor_user_id == User.id)
    )

    count_query = select(func.count()).select_from(AuditLog)

    if action:
        query = query.where(AuditLog.action == action)
        count_query = count_query.where(AuditLog.action == action)
    if entity_type:
        query = query.where(AuditLog.entity_type == entity_type)
        count_query = count_query.where(AuditLog.entity_type == entity_type)
    if actor_user_id:
        query = query.where(AuditLog.actor_user_id == actor_user_id)
        count_query = count_query.where(AuditLog.actor_user_id == actor_user_id)

    total = db.scalar(count_query) or 0

    rows = db.execute(
        query.order_by(AuditLog.id.desc()).limit(limit).offset(offset)
    ).mappings().all()

    items = [AuditLogRead(**dict(row)) for row in rows]

    return AuditLogPage(items=items, total=total, limit=limit, offset=offset)
