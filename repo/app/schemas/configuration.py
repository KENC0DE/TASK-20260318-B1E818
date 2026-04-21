"""Operation Configuration pydantic schemas."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class ConfigurationCreate(BaseModel):
    config_key: str
    config_value: dict[str, Any]
    rollout_percentage: int = 100


class ConfigurationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    config_key: str
    config_value: dict[str, Any]
    version: int
    rollout_percentage: int
    is_active: bool
    created_at: datetime
    updated_at: datetime
