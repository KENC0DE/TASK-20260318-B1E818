"""Unit tests for OrderService."""

from __future__ import annotations

import uuid
from decimal import Decimal
from datetime import datetime, UTC, timedelta

import pytest
from sqlalchemy.orm import Session

from app.models.auth import User, UserRole
from app.models.product import Product
from app.models.cart import Cart, CartItem
from app.models.order import Order
from app.services.order import OrderService


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
def product(db_session: Session) -> Product:
    product = Product(
        name="Test Product",
        barcode=f"999{uuid.uuid4().hex[:6]}",
        price=Decimal("100.00"),
        stock=10,
        is_active=True,
    )
    db_session.add(product)
    db_session.commit()
    return product


def test_create_order_from_items(db_session: Session, cashier: User, product: Product) -> None:
    items = [{"product_id": str(product.id), "quantity": 2}]
    order = OrderService.create_order(db_session, cashier.id, items=items)
    
    assert order.id is not None
    assert order.status == "pending"
    assert order.total == Decimal("200.00")
    assert len(order.lines) == 1
    assert order.lines[0].product_id == product.id
    assert order.lines[0].quantity == 2


def test_create_order_from_cart(db_session: Session, cashier: User, product: Product) -> None:
    cart = Cart(created_by=cashier.id, status="active")
    db_session.add(cart)
    db_session.flush()
    
    cart_item = CartItem(
        cart_id=cart.id,
        product_id=product.id,
        quantity=3,
        unit_price=product.price
    )
    db_session.add(cart_item)
    db_session.commit()
    
    order = OrderService.create_order(db_session, cashier.id, cart_id=cart.id)
    
    assert order.total == Decimal("300.00")
    assert len(order.lines) == 1


def test_void_order_success(db_session: Session, cashier: User, product: Product) -> None:
    items = [{"product_id": str(product.id), "quantity": 1}]
    order = OrderService.create_order(db_session, cashier.id, items=items)
    
    voided = OrderService.void_order(db_session, order.id, cashier.id)
    assert voided.status == "voided"
    assert voided.voided_at is not None


def test_auto_void_pending_orders(db_session: Session, cashier: User, product: Product) -> None:
    # Create an old pending order
    order = Order(
        cashier_id=cashier.id,
        status="pending",
        subtotal=Decimal("100"),
        total=Decimal("100"),
        created_at=datetime.now(UTC) - timedelta(minutes=31)
    )
    db_session.add(order)
    db_session.commit()
    
    count = OrderService.auto_void_pending_orders(db_session)
    assert count == 1
    
    db_session.refresh(order)
    assert order.status == "voided"
