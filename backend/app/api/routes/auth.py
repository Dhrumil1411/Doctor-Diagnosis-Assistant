from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.security import create_access_token, verify_password
from app.db.base import get_db
from app.models.users import User
from app.schemas.auth import Token
from app.schemas.user import UserRead
from app.services.audit import record_audit

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login", response_model=Token)
def login(
    request: Request,
    form: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
) -> Token:
    client_ip = request.client.host if request.client else None
    user = db.scalar(select(User).where(User.email == form.username.lower()))
    if user is None or not verify_password(form.password, user.hashed_password):
        record_audit(
            db,
            actor_user_id=user.id if user else None,
            action="login_failed",
            entity_type="user",
            detail={"email": form.username.lower()},
            ip_address=client_ip,
        )
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Account is disabled"
        )
    record_audit(
        db,
        actor_user_id=user.id,
        action="login_success",
        entity_type="user",
        entity_id=user.id,
        ip_address=client_ip,
    )
    db.commit()
    return Token(access_token=create_access_token(user.id, user.role.value))


@router.get("/me", response_model=UserRead)
def me(current_user: User = Depends(get_current_user)) -> User:
    return current_user
