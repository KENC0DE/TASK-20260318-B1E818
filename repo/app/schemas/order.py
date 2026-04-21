"""Order pydantic schemas."""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class OrderLineResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    product_id: uuid.UUID
    product_name: str | None = None
    quantity: int
    unit_price: Decimal
    line_discount: Decimal
    line_total: Decimal
    promotion_rule_id: uuid.UUID | None = None


class OrderResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    cashier_id: uuid.UUID
    status: str
    subtotal: Decimal
    discount_total: Decimal
    total: Decimal
    created_at: datetime
    settled_at: datetime | None = None
    voided_at: datetime | None = None
    lines: list[OrderLineResponse]


class OrderCreateRequest(BaseModel):
    items: list[dict[str, Any]] | None = None
    apply_promotions: bool = True
    cart_id: uuid.UUID | None = None


class OrderListResponse(BaseModel):
    items: list[OrderResponse]
    total: int
    page: int
    page_size: int


class ReceiptResponse(BaseModel):
    order_id: uuid.UUID
    lines: list[dict[str, Any]]
    total: Decimal
    subtotal: Decimal
    discount_total: Decimal
    payments: list[dict[str, Any]] = []
    issued_at: datetime
