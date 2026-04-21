"""Notification domain service."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, UTC
from typing import Any

from sqlalchemy.orm import Session
from sqlalchemy import select, update, and_

from app.models.notification import Notification, NotificationThrottle


class NotificationService:
    @staticmethod
    def dispatch(
        db: Session,
        event_type: str,
        object_id: uuid.UUID | None,
        recipient_ids: list[uuid.UUID],
        message: str,
        object_type: str | None = None
    ) -> list[Notification]:
        """
        Dispatch notifications to recipients with throttling.
        Throttle: 10 minutes per (event_type, object_id).
        """
        # 1. Throttle check
        if object_id:
            throttle = db.query(NotificationThrottle).filter(
                and_(
                    NotificationThrottle.event_type == event_type,
                    NotificationThrottle.object_id == object_id
                )
            ).first()

            now = datetime.now(UTC)
            if throttle:
                last_sent = throttle.last_sent_at
                if last_sent.tzinfo is None:
                    last_sent = last_sent.replace(tzinfo=UTC)
                
                if now < last_sent + timedelta(minutes=10):
                    # Throttled, skip dispatch
                    return []
                else:
                    throttle.last_sent_at = now
            else:
                throttle = NotificationThrottle(
                    event_type=event_type,
                    object_id=object_id,
                    last_sent_at=now
                )
                db.add(throttle)
        
        # 2. Create notifications
        notifications = []
        for recipient_id in recipient_ids:
            notification = Notification(
                recipient_id=recipient_id,
                event_type=event_type,
                object_type=object_type,
                object_id=object_id,
                message=message,
                delivered_at=datetime.now(UTC)
            )
            db.add(notification)
            notifications.append(notification)
        
        db.commit()
        return notifications

    @staticmethod
    def get_notifications(
        db: Session,
        user_id: uuid.UUID,
        page: int = 1,
        page_size: int = 20
    ) -> tuple[list[Notification], int]:
        """
        Retrieve paginated notifications for a user.
        """
        query = db.query(Notification).filter(Notification.recipient_id == user_id)
        total = query.count()
        items = (
            query.order_by(Notification.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )
        return items, total

    @staticmethod
    def mark_as_read(db: Session, notification_id: uuid.UUID, user_id: uuid.UUID) -> Notification | None:
        """
        Mark a notification as read.
        """
        notification = db.get(Notification, notification_id)
        if not notification:
            return None
        
        if notification.recipient_id != user_id:
            raise PermissionError("Not authorized to mark this notification as read")
        
        if not notification.read_at:
            notification.read_at = datetime.now(UTC)
            db.commit()
            db.refresh(notification)
        
        return notification
