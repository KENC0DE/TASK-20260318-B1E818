"""Unit tests for FeatureService."""

from __future__ import annotations

import uuid
from datetime import datetime, UTC, timedelta

import pytest
from sqlalchemy.orm import Session

from app.models.feature import FeatureDefinition, FeatureValue
from app.services.feature import FeatureService


def test_create_definition(db_session: Session) -> None:
    data = {
        "name": "avg_order_value",
        "description": "Average order value for a user",
        "data_type": "float",
        "ttl_seconds": 3600,
        "computation_logic": {"type": "sliding_window"}
    }
    definition = FeatureService.create_definition(db_session, data)
    
    assert definition.id is not None
    assert definition.name == "avg_order_value"
    assert definition.data_type == "float"


def test_get_definitions(db_session: Session) -> None:
    FeatureService.create_definition(db_session, {
        "name": "feat1",
        "data_type": "string",
        "ttl_seconds": 60
    })
    FeatureService.create_definition(db_session, {
        "name": "feat2",
        "data_type": "int",
        "ttl_seconds": 60
    })
    
    definitions = FeatureService.get_definitions(db_session)
    assert len(definitions) >= 2


def test_compute_feature_new(db_session: Session) -> None:
    FeatureService.create_definition(db_session, {
        "name": "user_loyalty",
        "data_type": "float",
        "ttl_seconds": 3600,
        "computation_logic": {"type": "correlation"}
    })
    
    value = FeatureService.compute_feature(db_session, "user_loyalty", "user_123")
    
    assert value.id is not None
    assert value.entity_id == "user_123"
    assert value.value == 0.85
    assert value.storage_tier == "hot"


def test_compute_feature_update(db_session: Session) -> None:
    FeatureService.create_definition(db_session, {
        "name": "order_freq",
        "data_type": "int",
        "ttl_seconds": 3600,
        "computation_logic": {"type": "frequency"}
    })
    
    # First computation
    val1 = FeatureService.compute_feature(db_session, "order_freq", "user_456", {"mock_value": 5})
    assert val1.value == 5
    
    # Second computation (update)
    val2 = FeatureService.compute_feature(db_session, "order_freq", "user_456", {"mock_value": 10})
    assert val2.value == 10
    assert val1.id == val2.id


def test_move_expired_hot_to_cold(db_session: Session) -> None:
    definition = FeatureService.create_definition(db_session, {
        "name": "expired_feat",
        "data_type": "string",
        "ttl_seconds": 10
    })
    
    # Create an expired value manually
    expired_val = FeatureValue(
        feature_id=definition.id,
        entity_id="entity_exp",
        value="old_data",
        storage_tier="hot",
        expires_at=datetime.now(UTC) - timedelta(seconds=10)
    )
    db_session.add(expired_val)
    
    # Create a non-expired value
    active_val = FeatureValue(
        feature_id=definition.id,
        entity_id="entity_act",
        value="new_data",
        storage_tier="hot",
        expires_at=datetime.now(UTC) + timedelta(seconds=100)
    )
    db_session.add(active_val)
    db_session.commit()
    
    count = FeatureService.move_expired_hot_to_cold(db_session)
    
    assert count == 1
    db_session.refresh(expired_val)
    db_session.refresh(active_val)
    assert expired_val.storage_tier == "cold"
    assert active_val.storage_tier == "hot"
