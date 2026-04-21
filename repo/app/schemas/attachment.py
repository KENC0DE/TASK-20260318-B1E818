"""Attachment pydantic schemas."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class AttachmentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    owner_type: str
    owner_id: uuid.UUID
    filename: str
    file_size: int
    mime_type: str
    sha256_fingerprint: str
    uploaded_by: uuid.UUID
    uploaded_at: datetime
