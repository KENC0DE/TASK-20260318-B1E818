"""Payment pydantic schemas."""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class PaymentItem(BaseModel):
    method: str = Field(..., description="cash / bank_card / stored_value")
    amount: Decimal


class PaymentCreateRequest(BaseModel):
    payments: list[PaymentItem]


class PaymentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    order_id: uuid.UUID
    method: str
    amount: Decimal
    recorded_at: datetime
