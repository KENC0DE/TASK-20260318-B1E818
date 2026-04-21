"""Unit tests for AnalyticsService."""

from __future__ import annotations

import uuid
from decimal import Decimal
from datetime import date, datetime, UTC, timedelta

import pytest
from sqlalchemy.orm import Session

from app.models.auth import User, UserRole
from app.models.order import Order
from app.models.after_sales import AfterSalesOrder
from app.services.analytics import AnalyticsService


@pytest.fixture
def store_manager(db_session: Session) -> User:
    user = User(
        username=f"manager_{uuid.uuid4().hex[:6]}",
        password_hash="hash",
        role=UserRole.STORE_MANAGER,
    )
    db_session.add(user)
    db_session.commit()
    return user


def test_get_daily_metrics(db_session: Session, store_manager: User) -> None:
    today = date.today()
    now = datetime.now(UTC)
    
    # 1. Create settled orders
    order1 = Order(
        cashier_id=store_manager.id,
        status="settled",
        total=Decimal("100.00"),
        settled_at=now,
        created_at=now
    )
    order2 = Order(
        cashier_id=store_manager.id,
        status="settled",
        total=Decimal("50.00"),
        settled_at=now,
        created_at=now
    )
    db_session.add_all([order1, order2])
    
    # 2. Create voided order
    order3 = Order(
        cashier_id=store_manager.id,
        status="voided",
        total=Decimal("20.00"),
        voided_at=now,
        created_at=now
    )
    db_session.add(order3)
    db_session.flush()
    
    # 3. Create after-sales request
    as_req = AfterSalesOrder(
        original_order_id=order1.id,
        type="return",
        status="pending",
        refund_amount=Decimal("50.00"),
        idempotency_key="ikey-analytics-1",
        created_by=store_manager.id,
        created_at=now
    )
    db_session.add(as_req)
    db_session.commit()
    
    metrics = AnalyticsService.get_daily_metrics(db_session, today)
    
    assert metrics.date == today
    assert metrics.transaction_volume == Decimal("150.00")
    # 2 settled, 1 voided -> 2 / (2+1) = 0.666...
    assert pytest.approx(metrics.conversion_rate) == 0.6666666666666666
    assert metrics.unique_active_users == 1
    # 1 after-sales, 2 settled -> 1 / 2 = 0.5
    assert metrics.dispute_rate == 0.5


def test_export_daily_metrics(db_session: Session, store_manager: User) -> None:
    today = date.today()
    csv_data = AnalyticsService.export_daily_metrics(db_session, today)
    assert "date,transaction_volume" in csv_data
    assert str(today) in csv_data
