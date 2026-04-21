"""Pydantic schemas for cart and cart pricing projection."""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class CartCreateResponse(BaseModel):
    id: uuid.UUID
    status: str
    created_at: datetime


class CartItemAddRequest(BaseModel):
    product_id: uuid.UUID
    quantity: int = Field(ge=1, le=9999)


class CartItemUpdateRequest(BaseModel):
    quantity: int = Field(ge=1, le=9999)


class CartItemResponse(BaseModel):
    id: uuid.UUID
    product_id: uuid.UUID
    product_name: str
    quantity: int
    unit_price: Decimal
    line_subtotal: Decimal


class AppliedPromotionResponse(BaseModel):
    rule_id: uuid.UUID
    rule_name: str
    rule_type: str
    discount_amount: Decimal
    details: dict


class CartPricingResponse(BaseModel):
    subtotal: Decimal
    discount_total: Decimal
    total: Decimal


class CartResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    status: str
    created_by: uuid.UUID
    items: list[CartItemResponse]
    pricing: CartPricingResponse
    applied_promotions: list[AppliedPromotionResponse]
    purchase_limit_violations: list[str]
    created_at: datetime
    updated_at: datetime
