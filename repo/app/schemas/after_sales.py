"""After-sales pydantic schemas."""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class AfterSalesCreateRequest(BaseModel):
    original_order_id: uuid.UUID
    type: str = Field(..., description="return / exchange")
    reason: str | None = None
    refund_amount: Decimal
    idempotency_key: str


class AfterSalesResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    original_order_id: uuid.UUID
    type: str
    status: str
    refund_amount: Decimal
    idempotency_key: str
    reason: str | None
    created_at: datetime
    completed_at: datetime | None
    created_by: uuid.UUID
