from __future__ import annotations

import pytest
from sqlalchemy.orm import Session
from app.services.configuration import ConfigurationService
from app.models.configuration import OperationConfiguration

def test_create_configuration(db_session: Session) -> None:
    data = {
        "config_key": "test_key",
        "config_value": {"foo": "bar"},
        "rollout_percentage": 50
    }
    config = ConfigurationService.create_configuration(db_session, data)
    
    assert config.config_key == "test_key"
    assert config.config_value == {"foo": "bar"}
    assert config.version == 1
    assert config.is_active is True

def test_create_configuration_increments_version(db_session: Session) -> None:
    ConfigurationService.create_configuration(db_session, {
        "config_key": "v_key",
        "config_value": {"v": 1}
    })
    
    config2 = ConfigurationService.create_configuration(db_session, {
        "config_key": "v_key",
        "config_value": {"v": 2}
    })
    
    assert config2.version == 2
    assert config2.is_active is True
    
    # Check that v1 is now inactive
    v1 = db_session.query(OperationConfiguration).filter(
        OperationConfiguration.config_key == "v_key",
        OperationConfiguration.version == 1
    ).first()
    assert v1.is_active is False

def test_get_active_configuration(db_session: Session) -> None:
    ConfigurationService.create_configuration(db_session, {
        "config_key": "active_key",
        "config_value": {"v": 1}
    })
    ConfigurationService.create_configuration(db_session, {
        "config_key": "active_key",
        "config_value": {"v": 2}
    })
    
    active = ConfigurationService.get_active_configuration(db_session, "active_key")
    assert active is not None
    assert active.version == 2
    assert active.config_value == {"v": 2}

def test_rollback_configuration(db_session: Session) -> None:
    ConfigurationService.create_configuration(db_session, {
        "config_key": "rb_key",
        "config_value": {"v": 1}
    })
    ConfigurationService.create_configuration(db_session, {
        "config_key": "rb_key",
        "config_value": {"v": 2}
    })
    
    rolled_back = ConfigurationService.rollback_configuration(db_session, "rb_key")
    assert rolled_back.version == 3
    assert rolled_back.config_value == {"v": 1}
    
    active = ConfigurationService.get_active_configuration(db_session, "rb_key")
    assert active.version == 3
    assert active.config_value == {"v": 1}

def test_rollback_configuration_fails_if_no_previous(db_session: Session) -> None:
    ConfigurationService.create_configuration(db_session, {
        "config_key": "no_prev",
        "config_value": {"v": 1}
    })
    
    with pytest.raises(ValueError, match="No previous version found"):
        ConfigurationService.rollback_configuration(db_session, "no_prev")
