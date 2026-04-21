"""Feature Library ORM models."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, Integer, String, Uuid, func, JSON, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class FeatureDefinition(Base):
    __tablename__ = "feature_definitions"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(128), unique=True, index=True, nullable=False)
    description: Mapped[str | None] = mapped_column(String(512), nullable=True)
    data_type: Mapped[str] = mapped_column(String(64), nullable=False)  # float, int, string, bool, json
    computation_logic: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    ttl_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=3600)  # Default 1 hour

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    values: Mapped[list[FeatureValue]] = relationship("FeatureValue", back_populates="definition", cascade="all, delete-orphan")


class FeatureValue(Base):
    __tablename__ = "feature_values"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    feature_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("feature_definitions.id"), nullable=False, index=True)
    entity_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    value: Mapped[Any] = mapped_column(JSON, nullable=False)
    storage_tier: Mapped[str] = mapped_column(String(32), nullable=False, default="hot")  # hot, cold
    
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    definition: Mapped[FeatureDefinition] = relationship("FeatureDefinition", back_populates="values")
