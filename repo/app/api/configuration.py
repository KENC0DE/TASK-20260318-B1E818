"""Operation Configuration API routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.auth import require_role
from app.db.session import get_db
from app.models.auth import User, UserRole
from app.schemas.configuration import ConfigurationCreate, ConfigurationResponse
from app.services.configuration import ConfigurationService

router = APIRouter(prefix="/config", tags=["Configuration"])


@router.post("", response_model=ConfigurationResponse, status_code=status.HTTP_201_CREATED)
def create_config(
    payload: ConfigurationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN)),
) -> ConfigurationResponse:
    """
    Create a new configuration version (Admin only).
    """
    config = ConfigurationService.create_configuration(db, payload.model_dump())
    return ConfigurationResponse.model_validate(config)


@router.get("/{key}", response_model=ConfigurationResponse)
def get_config(
    key: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.CASHIER, UserRole.STORE_MANAGER, UserRole.APPLICANT, UserRole.REVIEWER, UserRole.ADMIN)),
) -> ConfigurationResponse:
    """
    Get the active configuration for a key.
    """
    config = ConfigurationService.get_active_configuration(db, key, user_id=current_user.id)
    if not config:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Configuration not found or not rolled out to this user")
    return ConfigurationResponse.model_validate(config)


@router.post("/{key}/rollback", response_model=ConfigurationResponse)
def rollback_config(
    key: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN)),
) -> ConfigurationResponse:
    """
    Rollback to the previous version (Admin only).
    """
    try:
        config = ConfigurationService.rollback_configuration(db, key)
        return ConfigurationResponse.model_validate(config)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/{key}/history", response_model=list[ConfigurationResponse])
def get_config_history(
    key: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN)),
) -> list[ConfigurationResponse]:
    """
    Get version history for a configuration key (Admin only).
    """
    history = ConfigurationService.get_configuration_history(db, key)
    return [ConfigurationResponse.model_validate(c) for c in history]
