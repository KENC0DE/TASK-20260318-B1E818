"""Feature Library pydantic schemas."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class FeatureDefinitionCreate(BaseModel):
    name: str
    description: str | None = None
    data_type: str
    computation_logic: dict[str, Any] | None = None
    ttl_seconds: int = 3600


class FeatureDefinitionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    description: str | None
    data_type: str
    computation_logic: dict[str, Any] | None
    ttl_seconds: int
    created_at: datetime
    updated_at: datetime


class FeatureComputeRequest(BaseModel):
    feature_name: str
    entity_id: str
    # Parameters for computation, e.g. window size or specific data points
    parameters: dict[str, Any] | None = None


class FeatureValueResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    feature_id: uuid.UUID
    entity_id: str
    value: Any
    storage_tier: str
    expires_at: datetime | None
    created_at: datetime
    updated_at: datetime
