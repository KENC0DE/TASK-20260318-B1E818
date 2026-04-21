"""Feature Library domain service."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, UTC
from typing import Any

from sqlalchemy.orm import Session
from sqlalchemy import select, update, and_, delete

from app.models.feature import FeatureDefinition, FeatureValue


class FeatureService:
    @staticmethod
    def create_definition(db: Session, data: dict[str, Any]) -> FeatureDefinition:
        definition = FeatureDefinition(**data)
        db.add(definition)
        db.commit()
        db.refresh(definition)
        return definition

    @staticmethod
    def get_definitions(db: Session) -> list[FeatureDefinition]:
        return db.query(FeatureDefinition).all()

    @staticmethod
    def get_definition_by_name(db: Session, name: str) -> FeatureDefinition | None:
        return db.query(FeatureDefinition).filter(FeatureDefinition.name == name).first()

    @staticmethod
    def compute_feature(
        db: Session, 
        feature_name: str, 
        entity_id: str, 
        parameters: dict[str, Any] | None = None
    ) -> FeatureValue:
        definition = FeatureService.get_definition_by_name(db, feature_name)
        if not definition:
            raise ValueError(f"Feature definition '{feature_name}' not found")

        # Simplified computation logic
        logic = (definition.computation_logic or {}).get("type", "static")
        computed_value = None

        if logic == "frequency":
            # Simplified: just return a dummy frequency or count something
            # In a real system, we'd query an events table
            computed_value = parameters.get("mock_value", 10) if parameters else 10
        elif logic == "sliding_window":
            # Simplified: return a dummy sum
            computed_value = parameters.get("mock_value", 100.5) if parameters else 100.5
        elif logic == "correlation":
            # Simplified: return a dummy correlation coefficient
            computed_value = 0.85
        else:
            computed_value = parameters.get("value", "default_value") if parameters else "default_value"

        # Create or update FeatureValue
        now = datetime.now(UTC)
        expires_at = now + timedelta(seconds=definition.ttl_seconds)

        feature_value = db.query(FeatureValue).filter(
            and_(
                FeatureValue.feature_id == definition.id,
                FeatureValue.entity_id == entity_id
            )
        ).first()

        if feature_value:
            feature_value.value = computed_value
            feature_value.expires_at = expires_at
            feature_value.storage_tier = "hot"
            feature_value.updated_at = now
        else:
            feature_value = FeatureValue(
                feature_id=definition.id,
                entity_id=entity_id,
                value=computed_value,
                storage_tier="hot",
                expires_at=expires_at
            )
            db.add(feature_value)

        db.commit()
        db.refresh(feature_value)
        return feature_value

    @staticmethod
    def get_feature_values(db: Session, feature_id: uuid.UUID | None = None) -> list[FeatureValue]:
        query = db.query(FeatureValue)
        if feature_id:
            query = query.filter(FeatureValue.feature_id == feature_id)
        return query.all()

    @staticmethod
    def move_expired_hot_to_cold(db: Session) -> int:
        """
        Move expired hot values to cold storage tier.
        """
        now = datetime.now(UTC)
        
        # Find hot values that are expired
        expired_values = db.query(FeatureValue).filter(
            and_(
                FeatureValue.storage_tier == "hot",
                FeatureValue.expires_at <= now
            )
        ).all()

        count = 0
        for val in expired_values:
            val.storage_tier = "cold"
            # Once moved to cold, we might nullify expires_at or keep it for final deletion
            # For now, let's just change the tier
            count += 1
        
        db.commit()
        return count
