"""Notification API routes."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.core.auth import require_role
from app.db.session import get_db
from app.models.auth import User, UserRole
from app.schemas.notification import (
    NotificationResponse,
    NotificationListResponse,
    NotificationDispatchRequest
)
from app.services.notification import NotificationService

router = APIRouter(prefix="/notifications", tags=["Notifications"])


@router.get("", response_model=NotificationListResponse)
def get_notifications(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.CASHIER, UserRole.STORE_MANAGER, UserRole.APPLICANT, UserRole.REVIEWER, UserRole.ADMIN)),
) -> NotificationListResponse:
    """
    Get authenticated user's notification inbox.
    """
    items, total = NotificationService.get_notifications(
        db=db,
        user_id=current_user.id,
        page=page,
        page_size=page_size
    )
    return NotificationListResponse(
        items=[NotificationResponse.model_validate(item) for item in items],
        total=total,
        page=page,
        page_size=page_size
    )


@router.post("/{notification_id}/read", response_model=NotificationResponse)
def mark_as_read(
    notification_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.CASHIER, UserRole.STORE_MANAGER, UserRole.APPLICANT, UserRole.REVIEWER, UserRole.ADMIN)),
) -> NotificationResponse:
    """
    Mark a notification as read.
    """
    try:
        notification = NotificationService.mark_as_read(
            db=db,
            notification_id=notification_id,
            user_id=current_user.id
        )
        if not notification:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found")
        return NotificationResponse.model_validate(notification)
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))


@router.post("/dispatch", response_model=list[NotificationResponse], status_code=status.HTTP_201_CREATED)
def dispatch_notification(
    payload: NotificationDispatchRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN)),
) -> list[NotificationResponse]:
    """
    Trigger a notification event (Admin only).
    """
    notifications = NotificationService.dispatch(
        db=db,
        event_type=payload.event_type,
        object_id=payload.object_id,
        recipient_ids=payload.recipient_ids,
        message=payload.message,
        object_type=payload.object_type
    )
    return [NotificationResponse.model_validate(n) for n in notifications]
