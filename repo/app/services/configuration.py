"""Operation Configuration domain service."""

from __future__ import annotations

import uuid
import hashlib
from typing import Any

from sqlalchemy.orm import Session
from sqlalchemy import desc, and_

from app.models.configuration import OperationConfiguration


class ConfigurationService:
    @staticmethod
    def create_configuration(db: Session, data: dict[str, Any]) -> OperationConfiguration:
        key = data["config_key"]
        
        # Deactivate previous active version
        db.query(OperationConfiguration).filter(
            and_(
                OperationConfiguration.config_key == key,
                OperationConfiguration.is_active == True
            )
        ).update({"is_active": False})

        # Get latest version number
        latest = db.query(OperationConfiguration).filter(
            OperationConfiguration.config_key == key
        ).order_by(desc(OperationConfiguration.version)).first()
        
        new_version = (latest.version + 1) if latest else 1

        config = OperationConfiguration(
            config_key=key,
            config_value=data["config_value"],
            version=new_version,
            rollout_percentage=data.get("rollout_percentage", 100),
            is_active=True
        )
        db.add(config)
        db.commit()
        db.refresh(config)
        return config

    @staticmethod
    def get_active_configuration(db: Session, key: str, user_id: uuid.UUID | None = None) -> OperationConfiguration | None:
        config = db.query(OperationConfiguration).filter(
            and_(
                OperationConfiguration.config_key == key,
                OperationConfiguration.is_active == True
            )
        ).first()
        
        if not config:
            return None
            
        if config.rollout_percentage >= 100:
            return config
            
        if user_id is None:
            # If no user context, we only return if 100% rollout
            return None
            
        # Deterministic rollout based on user_id hash
        # Use first 4 bytes of UUID hash to get a value between 0-99
        user_hash = int(hashlib.md5(str(user_id).encode()).hexdigest()[:8], 16)
        if (user_hash % 100) < config.rollout_percentage:
            return config
            
        return None

    @staticmethod
    def get_configuration_history(db: Session, key: str) -> list[OperationConfiguration]:
        return db.query(OperationConfiguration).filter(
            OperationConfiguration.config_key == key
        ).order_by(desc(OperationConfiguration.version)).all()

    @staticmethod
    def rollback_configuration(db: Session, key: str) -> OperationConfiguration:
        # Get current active config
        current_active = ConfigurationService.get_active_configuration(db, key)
        if not current_active:
            raise ValueError(f"No active configuration found for key: {key}")

        # Find the previous version
        previous = db.query(OperationConfiguration).filter(
            and_(
                OperationConfiguration.config_key == key,
                OperationConfiguration.version < current_active.version
            )
        ).order_by(desc(OperationConfiguration.version)).first()

        if not previous:
            raise ValueError(f"No previous version found for key: {key}")

        # Create a new version that is a copy of the previous one
        return ConfigurationService.create_configuration(db, {
            "config_key": key,
            "config_value": previous.config_value,
            "rollout_percentage": previous.rollout_percentage
        })
