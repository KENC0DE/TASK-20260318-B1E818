"""After-sales API routes."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.auth import require_role
from app.db.session import get_db
from app.models.auth import User, UserRole
from app.schemas.after_sales import AfterSalesCreateRequest, AfterSalesResponse
from app.services.after_sales import AfterSalesService

router = APIRouter(prefix="/after-sales", tags=["After-Sales"])


@router.post("", response_model=AfterSalesResponse, status_code=status.HTTP_201_CREATED)
def create_after_sales_request(
    payload: AfterSalesCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.CASHIER, UserRole.STORE_MANAGER)),
) -> AfterSalesResponse:
    try:
        after_sales = AfterSalesService.create_request(
            db=db,
            cashier_id=current_user.id,
            original_order_id=payload.original_order_id,
            after_sales_type=payload.type,
            refund_amount=payload.refund_amount,
            idempotency_key=payload.idempotency_key,
            reason=payload.reason
        )
        return AfterSalesResponse.model_validate(after_sales)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get("/{after_sales_id}", response_model=AfterSalesResponse)
def get_after_sales_request(
    after_sales_id: uuid.UUID,
    db: Session = Depends(get_db),
    _: User = Depends(require_role(UserRole.CASHIER, UserRole.STORE_MANAGER, UserRole.ADMIN)),
) -> AfterSalesResponse:
    after_sales = AfterSalesService.get_request(db, after_sales_id)
    if not after_sales:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="After-sales request not found")
    return AfterSalesResponse.model_validate(after_sales)


@router.post("/{after_sales_id}/complete", response_model=AfterSalesResponse)
def complete_after_sales(
    after_sales_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.STORE_MANAGER, UserRole.ADMIN)),
) -> AfterSalesResponse:
    try:
        after_sales = AfterSalesService.complete_after_sales(db, after_sales_id, current_user.id)
        if not after_sales:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="After-sales request not found")
        return AfterSalesResponse.model_validate(after_sales)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
