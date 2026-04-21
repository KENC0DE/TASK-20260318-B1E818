"""Unit tests for NotificationService."""

from __future__ import annotations

import uuid
import pytest
from datetime import datetime, timedelta, UTC
from sqlalchemy.orm import Session

from app.models.auth import User, UserRole
from app.models.notification import Notification, NotificationThrottle
from app.services.notification import NotificationService


@pytest.fixture
def recipient(db_session: Session) -> User:
    user = User(
        username=f"user_{uuid.uuid4().hex[:6]}",
        password_hash="hash",
        role=UserRole.APPLICANT,
    )
    db_session.add(user)
    db_session.commit()
    return user


def test_dispatch_success(db_session: Session, recipient: User) -> None:
    event_type = "test_event"
    object_id = uuid.uuid4()
    message = "Test message"
    
    notifications = NotificationService.dispatch(
        db=db_session,
        event_type=event_type,
        object_id=object_id,
        recipient_ids=[recipient.id],
        message=message
    )
    
    assert len(notifications) == 1
    assert notifications[0].recipient_id == recipient.id
    assert notifications[0].event_type == event_type
    assert notifications[0].object_id == object_id
    assert notifications[0].message == message
    assert notifications[0].delivered_at is not None


def test_dispatch_throttling(db_session: Session, recipient: User) -> None:
    event_type = "throttle_event"
    object_id = uuid.uuid4()
    message = "Message 1"
    
    # First dispatch
    notifications1 = NotificationService.dispatch(
        db=db_session,
        event_type=event_type,
        object_id=object_id,
        recipient_ids=[recipient.id],
        message=message
    )
    assert len(notifications1) == 1
    
    # Second dispatch (immediate) - should be throttled
    notifications2 = NotificationService.dispatch(
        db=db_session,
        event_type=event_type,
        object_id=object_id,
        recipient_ids=[recipient.id],
        message="Message 2"
    )
    assert len(notifications2) == 0
    
    # Manually update throttle to 11 minutes ago
    throttle = db_session.query(NotificationThrottle).filter_by(
        event_type=event_type, object_id=object_id
    ).first()
    throttle.last_sent_at = datetime.now(UTC) - timedelta(minutes=11)
    db_session.commit()
    
    # Third dispatch - should NOT be throttled
    notifications3 = NotificationService.dispatch(
        db=db_session,
        event_type=event_type,
        object_id=object_id,
        recipient_ids=[recipient.id],
        message="Message 3"
    )
    assert len(notifications3) == 1


def test_get_notifications(db_session: Session, recipient: User) -> None:
    # Create some notifications
    for i in range(5):
        NotificationService.dispatch(
            db=db_session,
            event_type=f"event_{i}",
            object_id=uuid.uuid4(),
            recipient_ids=[recipient.id],
            message=f"msg_{i}"
        )
    
    items, total = NotificationService.get_notifications(db_session, recipient.id, page=1, page_size=2)
    assert total == 5
    assert len(items) == 2


def test_mark_as_read(db_session: Session, recipient: User) -> None:
    notifications = NotificationService.dispatch(
        db=db_session,
        event_type="event",
        object_id=uuid.uuid4(),
        recipient_ids=[recipient.id],
        message="msg"
    )
    notification_id = notifications[0].id
    
    # Mark as read
    updated = NotificationService.mark_as_read(db_session, notification_id, recipient.id)
    assert updated.read_at is not None
    
    # Try marking as read by another user
    other_user_id = uuid.uuid4()
    with pytest.raises(PermissionError):
        NotificationService.mark_as_read(db_session, notification_id, other_user_id)
