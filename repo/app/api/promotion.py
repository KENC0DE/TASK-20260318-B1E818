"""Promotion rule CRUD routes."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.auth import require_role
from app.db.session import get_db
from app.models.auth import User, UserRole
from app.models.promotion import PromotionRule, PromotionRuleType
from app.schemas.promotion import (
    PromotionRuleCreateRequest,
    PromotionRuleListResponse,
    PromotionRuleResponse,
    PromotionRuleUpdateRequest,
)
from app.services.promotion import PromotionService

router = APIRouter(prefix="/promotions", tags=["Promotions"])


@router.post("", response_model=PromotionRuleResponse, status_code=status.HTTP_201_CREATED)
def create_promotion_rule(
    payload: PromotionRuleCreateRequest,
    db: Session = Depends(get_db),
    _: User = Depends(require_role(UserRole.STORE_MANAGER, UserRole.ADMIN)),
) -> PromotionRuleResponse:
    try:
        PromotionService.validate_time_window(payload.start_at, payload.end_at)
        normalized = PromotionService.validate_config(payload.rule_type, payload.config)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    rule = PromotionRule(
        name=payload.name.strip(),
        rule_type=payload.rule_type,
        priority=payload.priority,
        is_active=payload.is_active,
        config_json=normalized,
        start_at=payload.start_at,
        end_at=payload.end_at,
    )
    db.add(rule)
    db.commit()
    db.refresh(rule)
    return PromotionRuleResponse(
        id=rule.id,
        name=rule.name,
        rule_type=rule.rule_type,
        priority=rule.priority,
        is_active=rule.is_active,
        config=rule.config_json,
        start_at=rule.start_at,
        end_at=rule.end_at,
        created_at=rule.created_at,
        updated_at=rule.updated_at,
    )


@router.get("", response_model=PromotionRuleListResponse)
def list_promotion_rules(
    rule_type: PromotionRuleType | None = Query(default=None),
    is_active: bool | None = Query(default=None),
    db: Session = Depends(get_db),
    _: User = Depends(require_role(UserRole.CASHIER, UserRole.STORE_MANAGER, UserRole.ADMIN)),
) -> PromotionRuleListResponse:
    query = db.query(PromotionRule)
    if rule_type is not None:
        query = query.filter(PromotionRule.rule_type == rule_type)
    if is_active is not None:
        query = query.filter(PromotionRule.is_active == is_active)

    items = query.order_by(PromotionRule.priority.asc(), PromotionRule.created_at.asc()).all()
    return PromotionRuleListResponse(
        items=[
            PromotionRuleResponse(
                id=item.id,
                name=item.name,
                rule_type=item.rule_type,
                priority=item.priority,
                is_active=item.is_active,
                config=item.config_json,
                start_at=item.start_at,
                end_at=item.end_at,
                created_at=item.created_at,
                updated_at=item.updated_at,
            )
            for item in items
        ],
        total=len(items),
    )


@router.put("/{rule_id}", response_model=PromotionRuleResponse)
def update_promotion_rule(
    rule_id: uuid.UUID,
    payload: PromotionRuleUpdateRequest,
    db: Session = Depends(get_db),
    _: User = Depends(require_role(UserRole.STORE_MANAGER, UserRole.ADMIN)),
) -> PromotionRuleResponse:
    rule = db.get(PromotionRule, rule_id)
    if rule is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Promotion rule not found")

    update_data = payload.model_dump(exclude_unset=True)
    if not update_data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No fields provided for update")

    start_at = update_data.get("start_at", rule.start_at)
    end_at = update_data.get("end_at", rule.end_at)

    try:
        PromotionService.validate_time_window(start_at, end_at)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    if "name" in update_data:
        rule.name = update_data["name"].strip()
    if "priority" in update_data:
        rule.priority = update_data["priority"]
    if "is_active" in update_data:
        rule.is_active = update_data["is_active"]
    if "start_at" in update_data:
        rule.start_at = update_data["start_at"]
    if "end_at" in update_data:
        rule.end_at = update_data["end_at"]
    if "config" in update_data:
        try:
            rule.config_json = PromotionService.validate_config(rule.rule_type, update_data["config"])
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    db.add(rule)
    db.commit()
    db.refresh(rule)
    return PromotionRuleResponse(
        id=rule.id,
        name=rule.name,
        rule_type=rule.rule_type,
        priority=rule.priority,
        is_active=rule.is_active,
        config=rule.config_json,
        start_at=rule.start_at,
        end_at=rule.end_at,
        created_at=rule.created_at,
        updated_at=rule.updated_at,
    )


@router.delete("/{rule_id}", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
def delete_promotion_rule(
    rule_id: uuid.UUID,
    db: Session = Depends(get_db),
    _: User = Depends(require_role(UserRole.STORE_MANAGER, UserRole.ADMIN)),
):
    rule = db.get(PromotionRule, rule_id)
    if rule is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Promotion rule not found")

    db.delete(rule)
    db.commit()
