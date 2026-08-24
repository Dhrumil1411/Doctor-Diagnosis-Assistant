import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import require_roles
from app.core.security import hash_password
from app.db.base import get_db
from app.models.users import User, UserRole
from app.schemas.user import UserAdminUpdate, UserCreate, UserRead
from app.services.audit import record_audit

router = APIRouter(prefix="/api/users", tags=["users"])


@router.get("", response_model=list[UserRead])
def list_users(
    db: Session = Depends(get_db),
    admin: User = Depends(require_roles(UserRole.admin)),
) -> list[User]:
    return list(db.scalars(select(User).order_by(User.created_at)).all())


@router.post("", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def create_user(
    payload: UserCreate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_roles(UserRole.admin)),
) -> User:
    email = payload.email.lower()
    if db.scalar(select(User).where(User.email == email)):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Email already registered"
        )
    user = User(
        email=email,
        hashed_password=hash_password(payload.password),
        full_name=payload.full_name,
        role=payload.role,
    )
    db.add(user)
    record_audit(
        db,
        actor_user_id=admin.id,
        action="user_created",
        entity_type="user",
        entity_id=user.id,
        detail={"email": email, "role": payload.role.value},
    )
    db.commit()
    db.refresh(user)
    return user


@router.patch("/{user_id}", response_model=UserRead)
def update_user(
    user_id: uuid.UUID,
    payload: UserAdminUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_roles(UserRole.admin)),
) -> User:
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )
    if user.id == admin.id and (
        (payload.role is not None and payload.role != admin.role)
        or payload.is_active is False
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Admins cannot demote or deactivate themselves",
        )
    changes = payload.model_dump(exclude_unset=True)
    for field, value in changes.items():
        setattr(user, field, value)
    record_audit(
        db,
        actor_user_id=admin.id,
        action="user_updated",
        entity_type="user",
        entity_id=user.id,
        detail=changes,
    )
    db.commit()
    db.refresh(user)
    return user
