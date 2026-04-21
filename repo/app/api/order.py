"""Order API routes."""

from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.auth import require_role
from app.db.session import get_db
from app.models.auth import User, UserRole
from app.schemas.order import (
    OrderCreateRequest,
    OrderListResponse,
    OrderResponse,
    ReceiptResponse,
)
from app.schemas.payment import PaymentCreateRequest, PaymentResponse
from app.services.order import OrderService
from app.services.payment import PaymentService

router = APIRouter(prefix="/orders", tags=["Orders"])


@router.post("", response_model=OrderResponse, status_code=status.HTTP_201_CREATED)
def create_order(
    payload: OrderCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.CASHIER, UserRole.STORE_MANAGER)),
) -> OrderResponse:
    try:
        order = OrderService.create_order(
            db=db,
            cashier_id=current_user.id,
            items=payload.items,
            cart_id=payload.cart_id,
            apply_promotions=payload.apply_promotions,
        )
        return OrderResponse.model_validate(order)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get("", response_model=OrderListResponse)
def list_orders(
    status: str | None = Query(default=None),
    from_date: datetime | None = Query(default=None),
    to_date: datetime | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    _: User = Depends(require_role(UserRole.STORE_MANAGER, UserRole.ADMIN)),
) -> OrderListResponse:
    items, total = OrderService.list_orders(
        db=db,
        status=status,
        from_date=from_date,
        to_date=to_date,
        page=page,
        page_size=page_size,
    )
    return OrderListResponse(
        items=[OrderResponse.model_validate(item) for item in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{order_id}", response_model=OrderResponse)
def get_order(
    order_id: uuid.UUID,
    db: Session = Depends(get_db),
    _: User = Depends(require_role(UserRole.CASHIER, UserRole.STORE_MANAGER, UserRole.ADMIN)),
) -> OrderResponse:
    order = OrderService.get_order_or_404(db, order_id)
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
    return OrderResponse.model_validate(order)


@router.get("/{order_id}/receipt", response_model=ReceiptResponse)
def get_receipt(
    order_id: uuid.UUID,
    db: Session = Depends(get_db),
    _: User = Depends(require_role(UserRole.CASHIER, UserRole.STORE_MANAGER)),
) -> ReceiptResponse:
    order = OrderService.get_order_or_404(db, order_id)
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
    
    payload = order.receipt_payload or OrderService.generate_receipt_payload(order)
    return ReceiptResponse(**payload)


@router.post("/{order_id}/void", response_model=OrderResponse)
def void_order(
    order_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.STORE_MANAGER, UserRole.ADMIN)),
) -> OrderResponse:
    try:
        order = OrderService.void_order(db, order_id, current_user.id)
        if not order:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
        return OrderResponse.model_validate(order)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


@router.post("/{order_id}/payments", response_model=list[PaymentResponse])
def record_payments(
    order_id: uuid.UUID,
    payload: PaymentCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.CASHIER, UserRole.STORE_MANAGER)),
) -> list[PaymentResponse]:
    try:
        records = PaymentService.record_payments(
            db=db,
            order_id=order_id,
            payments=[p.model_dump() for p in payload.payments],
            cashier_id=current_user.id
        )
        return [PaymentResponse.model_validate(r) for r in records]
    except ValueError as exc:
        msg = str(exc)
        if "not found" in msg:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=msg) from exc
        if "already settled" in msg or "voided" in msg:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=msg) from exc
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=msg) from exc
