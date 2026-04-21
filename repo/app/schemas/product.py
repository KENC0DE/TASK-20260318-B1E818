"""Pydantic schemas for products."""

from __future__ import annotations

import enum
import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ProductSearchMode(str, enum.Enum):
    AUTO = "auto"
    BARCODE = "barcode"
    PINYIN = "pinyin"
    INTERNAL_CODE = "internal_code"


class ProductCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=256)
    barcode: str | None = Field(default=None, min_length=1, max_length=64)
    internal_code: str | None = Field(default=None, min_length=1, max_length=64)
    pinyin_code: str | None = Field(default=None, min_length=1, max_length=256)
    price: Decimal = Field(gt=0)
    stock: int = Field(default=0, ge=0)
    is_active: bool = True

    @field_validator("name", "barcode", "internal_code", "pinyin_code", mode="before")
    @classmethod
    def normalize_optional_strings(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = str(value).strip()
        return normalized or None


class ProductUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=256)
    barcode: str | None = Field(default=None, min_length=1, max_length=64)
    internal_code: str | None = Field(default=None, min_length=1, max_length=64)
    pinyin_code: str | None = Field(default=None, min_length=1, max_length=256)
    price: Decimal | None = Field(default=None, gt=0)
    stock: int | None = Field(default=None, ge=0)
    is_active: bool | None = None

    @field_validator("name", "barcode", "internal_code", "pinyin_code", mode="before")
    @classmethod
    def normalize_optional_strings(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = str(value).strip()
        return normalized or None


class ProductResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    barcode: str | None
    internal_code: str | None
    pinyin_code: str | None
    price: Decimal
    stock: int
    is_active: bool
    created_at: datetime
    updated_at: datetime


class ProductSearchResponse(BaseModel):
    items: list[ProductResponse]
    total: int
    page: int
    page_size: int