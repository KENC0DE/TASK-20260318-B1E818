"""Pydantic schemas for promotions."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.promotion import PromotionRuleType


class PromotionRuleCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    rule_type: PromotionRuleType
    priority: int = Field(default=100, ge=1, le=1000)
    is_active: bool = True
    config: dict
    start_at: datetime | None = None
    end_at: datetime | None = None


class PromotionRuleUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=128)
    priority: int | None = Field(default=None, ge=1, le=1000)
    is_active: bool | None = None
    config: dict | None = None
    start_at: datetime | None = None
    end_at: datetime | None = None


class PromotionRuleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    rule_type: PromotionRuleType
    priority: int
    is_active: bool
    config: dict
    start_at: datetime | None
    end_at: datetime | None
    created_at: datetime
    updated_at: datetime


class PromotionRuleListResponse(BaseModel):
    items: list[PromotionRuleResponse]
    total: int
