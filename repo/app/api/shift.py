from __future__ import annotations

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.audit import AuditService
from app.core.auth import require_role
from app.db.session import get_db
from app.models.auth import User, UserRole

router = APIRouter(prefix="/shifts", tags=["Shift"])


@router.post("/open", status_code=status.HTTP_200_OK)
def open_shift(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.CASHIER, UserRole.STORE_MANAGER)),
):
    AuditService.write(
        db,
        action="shift_open",
        actor_id=current_user.id,
        target_type="shift",
        metadata={"user_role": current_user.role.value},
    )
    db.commit()
    return {"message": "Shift opened"}


@router.post("/close", status_code=status.HTTP_200_OK)
def close_shift(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.CASHIER, UserRole.STORE_MANAGER)),
):
    AuditService.write(
        db,
        action="shift_close",
        actor_id=current_user.id,
        target_type="shift",
        metadata={"user_role": current_user.role.value},
    )
    db.commit()
    return {"message": "Shift closed"}
