"""Auth and user management API routes."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.audit import AuditService
from app.core.auth import AuthService, LoginService, get_current_user, require_role
from app.core.config import settings
from app.core.encryption import decrypt_text, encrypt_text
from app.db.session import get_db
from app.models.auth import User, UserRole
from app.schemas.auth import (
    LoginRequest,
    LoginResponse,
    UserCreateRequest,
    UserProfileResponse,
    UserResponse,
    UserRoleUpdateRequest,
)

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/login", response_model=LoginResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> LoginResponse:
    user = db.query(User).filter(User.username == payload.username).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )

    if LoginService.is_locked(user):
        retry_after_seconds = LoginService.lock_remaining_seconds(user)
        raise HTTPException(
            status_code=status.HTTP_423_LOCKED,
            detail={
                "msg": "Account locked. Try again later.",
                "retry_after_seconds": retry_after_seconds,
            },
        )

    if not AuthService.verify_password(payload.password, user.password_hash):
        LoginService.register_failed_attempt(user)
        db.add(user)
        db.commit()

        if LoginService.is_locked(user):
            raise HTTPException(
                status_code=status.HTTP_423_LOCKED,
                detail={
                    "msg": "Account locked. Try again later.",
                    "retry_after_seconds": LoginService.lock_remaining_seconds(user),
                },
            )

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )

    LoginService.register_success(user)
    db.add(user)
    AuditService.write(db, action="login", actor_id=user.id, target_type="user", target_id=user.id)
    db.commit()

    token = AuthService.create_access_token(user.id, user.role)
    return LoginResponse(
        access_token=token,
        expires_in=settings.jwt_access_token_expire_hours * 3600,
    )


@router.post("/users", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def create_user(
    payload: UserCreateRequest,
    db: Session = Depends(get_db),
    _: User = Depends(require_role(UserRole.ADMIN)),
) -> UserResponse:
    user = User(
        username=payload.username,
        password_hash=AuthService.hash_password(payload.password),
        role=payload.role,
        email=payload.email,
        contact=payload.contact,
    )
    db.add(user)

    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username already exists",
        ) from exc

    db.refresh(user)
    return UserResponse.model_validate(user)


@router.get("/users/{user_id}", response_model=UserProfileResponse)
def get_user_profile(
    user_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> UserProfileResponse:
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    if current_user.role != UserRole.ADMIN and current_user.id != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")

    return UserProfileResponse(
        id=user.id,
        username=user.username,
        role=user.role,
        created_at=user.created_at,
        email=user.email if current_user.role == UserRole.ADMIN or current_user.id == user.id else None,
        contact=user.contact if current_user.role == UserRole.ADMIN or current_user.id == user.id else None,
    )


@router.put("/users/{user_id}/role", response_model=UserResponse)
def update_user_role(
    user_id: uuid.UUID,
    payload: UserRoleUpdateRequest,
    db: Session = Depends(get_db),
    actor: User = Depends(require_role(UserRole.ADMIN)),
) -> UserResponse:
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    user.role = payload.role
    user.updated_at = datetime.now(UTC)
    db.add(user)
    AuditService.write(
        db,
        action="permission_change",
        actor_id=actor.id,
        target_type="user",
        target_id=user.id,
        metadata={"new_role": payload.role.value},
    )
    db.commit()
    db.refresh(user)
    return UserResponse.model_validate(user)
