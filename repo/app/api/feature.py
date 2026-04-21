"""Feature Library API routes."""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.core.auth import require_role
from app.db.session import get_db
from app.models.auth import User, UserRole
from app.schemas.feature import (
    FeatureDefinitionCreate,
    FeatureDefinitionResponse,
    FeatureComputeRequest,
    FeatureValueResponse
)
from app.services.feature import FeatureService

router = APIRouter(prefix="/features", tags=["Features"])


@router.post("/definitions", response_model=FeatureDefinitionResponse, status_code=status.HTTP_201_CREATED)
def create_definition(
    payload: FeatureDefinitionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN)),
) -> FeatureDefinitionResponse:
    """
    Create a new feature definition (Admin only).
    """
    try:
        definition = FeatureService.create_definition(db, payload.model_dump())
        return FeatureDefinitionResponse.model_validate(definition)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/definitions", response_model=list[FeatureDefinitionResponse])
def get_definitions(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN)),
) -> list[FeatureDefinitionResponse]:
    """
    List all feature definitions (Admin only).
    """
    definitions = FeatureService.get_definitions(db)
    return [FeatureDefinitionResponse.model_validate(d) for d in definitions]


@router.post("/compute", response_model=FeatureValueResponse)
def compute_feature(
    payload: FeatureComputeRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN)),
) -> FeatureValueResponse:
    """
    Compute a feature value for an entity (Admin only).
    """
    try:
        value = FeatureService.compute_feature(
            db=db,
            feature_name=payload.feature_name,
            entity_id=payload.entity_id,
            parameters=payload.parameters
        )
        return FeatureValueResponse.model_validate(value)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/values", response_model=list[FeatureValueResponse])
def get_values(
    feature_id: uuid.UUID | None = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN)),
) -> list[FeatureValueResponse]:
    """
    List feature values (Admin only).
    """
    values = FeatureService.get_feature_values(db, feature_id)
    return [FeatureValueResponse.model_validate(v) for v in values]
