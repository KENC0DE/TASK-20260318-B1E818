"""Promotion ORM model."""

from __future__ import annotations

import enum
import uuid
from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, Enum, Integer, String, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class PromotionRuleType(str, enum.Enum):
    SPEND_AND_SAVE = "spend_and_save"
    BUY_AND_GET = "buy_and_get"
    TIERED_PRICING = "tiered_pricing"
    PURCHASE_LIMIT = "purchase_limit"


class PromotionRule(Base):
    __tablename__ = "promotion_rules"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    rule_type: Mapped[PromotionRuleType] = mapped_column(
        Enum(PromotionRuleType, name="promotion_rule_type"), nullable=False
    )
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=100)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    config_json: Mapped[dict] = mapped_column("config", JSON, nullable=False)
    start_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    end_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )
