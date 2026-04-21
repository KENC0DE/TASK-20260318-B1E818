"""Unit tests for PaymentService."""

from __future__ import annotations

import uuid
from decimal import Decimal

import pytest
from sqlalchemy.orm import Session

from app.models.auth import User, UserRole
from app.models.order import Order
from app.services.payment import PaymentService


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
def pending_order(db_session: Session, cashier: User) -> Order:
    order = Order(
        cashier_id=cashier.id,
        status="pending",
        subtotal=Decimal("100.00"),
        total=Decimal("100.00"),
    )
    db_session.add(order)
    db_session.commit()
    return order


def test_record_single_payment_success(db_session: Session, cashier: User, pending_order: Order) -> None:
    payments = [{"method": "cash", "amount": 100.00}]
    records = PaymentService.record_payments(db_session, pending_order.id, payments, cashier.id)
    
    assert len(records) == 1
    assert records[0].amount == Decimal("100.00")
    assert pending_order.status == "settled"
    assert pending_order.settled_at is not None


def test_record_split_payment_success(db_session: Session, cashier: User, pending_order: Order) -> None:
    payments = [
        {"method": "cash", "amount": 40.00},
        {"method": "bank_card", "amount": 60.00}
    ]
    records = PaymentService.record_payments(db_session, pending_order.id, payments, cashier.id)
    
    assert len(records) == 2
    assert sum(r.amount for r in records) == Decimal("100.00")
    assert pending_order.status == "settled"


def test_record_payment_mismatch_fails(db_session: Session, cashier: User, pending_order: Order) -> None:
    payments = [{"method": "cash", "amount": 99.00}]
    with pytest.raises(ValueError, match="does not match order total"):
        PaymentService.record_payments(db_session, pending_order.id, payments, cashier.id)


def test_record_payment_already_settled_fails(db_session: Session, cashier: User, pending_order: Order) -> None:
    pending_order.status = "settled"
    db_session.commit()
    
    payments = [{"method": "cash", "amount": 100.00}]
    with pytest.raises(ValueError, match="already settled"):
        PaymentService.record_payments(db_session, pending_order.id, payments, cashier.id)
