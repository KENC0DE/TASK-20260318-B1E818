"""Unit tests for AfterSalesService."""

from __future__ import annotations

import uuid
from decimal import Decimal
from datetime import datetime, UTC, timedelta

import pytest
from sqlalchemy.orm import Session

from app.models.auth import User, UserRole
from app.models.order import Order
from app.models.after_sales import AfterSalesOrder
from app.services.after_sales import AfterSalesService


@pytest.fixture
def cashier(db_session: Session) -> User:
    user = User(
        username=f"cashier_{uuid.uuid4().hex[:6]}",
        password_hash="hash",
        role=UserRole.CASHIER,
    )
    db_session.add(user)
    db_session.commit()
    return user


@pytest.fixture
def settled_order(db_session: Session, cashier: User) -> Order:
    order = Order(
        cashier_id=cashier.id,
        status="settled",
        subtotal=Decimal("100.00"),
        total=Decimal("100.00"),
        created_at=datetime.now(UTC)
    )
    db_session.add(order)
    db_session.commit()
    return order


def test_create_after_sales_success(db_session: Session, cashier: User, settled_order: Order) -> None:
    ikey = "key-123"
    request = AfterSalesService.create_request(
        db_session, cashier.id, settled_order.id, "return", Decimal("50.00"), ikey
    )
    
    assert request.id is not None
    assert request.idempotency_key == ikey
    assert request.status == "pending"


def test_create_after_sales_idempotency(db_session: Session, cashier: User, settled_order: Order) -> None:
    ikey = "key-dup"
    req1 = AfterSalesService.create_request(
        db_session, cashier.id, settled_order.id, "return", Decimal("50.00"), ikey
    )
    req2 = AfterSalesService.create_request(
        db_session, cashier.id, settled_order.id, "return", Decimal("50.00"), ikey
    )
    
    assert req1.id == req2.id


def test_create_after_sales_exceeds_amount_fails(db_session: Session, cashier: User, settled_order: Order) -> None:
    with pytest.raises(ValueError, match="exceeds original order total"):
        AfterSalesService.create_request(
            db_session, cashier.id, settled_order.id, "return", Decimal("101.00"), "key-err"
        )


def test_complete_after_sales_success(db_session: Session, cashier: User, settled_order: Order) -> None:
    request = AfterSalesService.create_request(
        db_session, cashier.id, settled_order.id, "return", Decimal("100.00"), "key-comp"
    )
    
    completed = AfterSalesService.complete_after_sales(db_session, request.id, cashier.id)
    assert completed.status == "completed"
    assert settled_order.status == "refunded"
