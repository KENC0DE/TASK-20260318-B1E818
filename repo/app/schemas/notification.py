"""Notification pydantic schemas."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class NotificationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    recipient_id: uuid.UUID
    event_type: str
    object_type: str | None = None
    object_id: uuid.UUID | None = None
    message: str
    delivered_at: datetime | None = None
    read_at: datetime | None = None
    created_at: datetime


class NotificationListResponse(BaseModel):
    items: list[NotificationResponse]
    total: int
    page: int
    page_size: int


class NotificationDispatchRequest(BaseModel):
    recipient_ids: list[uuid.UUID]
    event_type: str
    object_type: str | None = None
    object_id: uuid.UUID | None = None
    message: str
