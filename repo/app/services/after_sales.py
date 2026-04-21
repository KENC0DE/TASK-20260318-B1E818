"""After-sales domain service."""

from __future__ import annotations

import uuid
from datetime import datetime, UTC, timedelta
from decimal import Decimal

from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.models.order import Order
from app.models.after_sales import AfterSalesOrder
from app.core.audit import AuditService


class AfterSalesService:
    @staticmethod
    def create_request(
        db: Session,
        cashier_id: uuid.UUID,
        original_order_id: uuid.UUID,
        after_sales_type: str,
        refund_amount: Decimal,
        idempotency_key: str,
        reason: str | None = None
    ) -> AfterSalesOrder:
        # Check idempotency
        existing = db.query(AfterSalesOrder).filter(AfterSalesOrder.idempotency_key == idempotency_key).first()
        if existing:
            return existing

        order = db.get(Order, original_order_id)
        if not order:
            raise ValueError("Original order not found")

        # 7-day window validation
        order_created_at = order.created_at
        if order_created_at.tzinfo is None:
            order_created_at = order_created_at.replace(tzinfo=UTC)
            
        if datetime.now(UTC) - order_created_at > timedelta(days=7):
            raise ValueError("Return window expired (over 7 days)")

        # Refund amount validation
        if refund_amount > order.total:
            raise ValueError("Refund amount exceeds original order total")
        if refund_amount <= 0:
            raise ValueError("Refund amount must be positive")

        after_sales = AfterSalesOrder(
            original_order_id=original_order_id,
            type=after_sales_type,
            status="pending",
            refund_amount=refund_amount,
            idempotency_key=idempotency_key,
            reason=reason,
            created_by=cashier_id
        )
        db.add(after_sales)
        
        try:
            db.commit()
            db.refresh(after_sales)
        except IntegrityError:
            db.rollback()
            # Double check if it was idempotency race
            existing = db.query(AfterSalesOrder).filter(AfterSalesOrder.idempotency_key == idempotency_key).first()
            if existing:
                return existing
            raise

        return after_sales

    @staticmethod
    def complete_after_sales(db: Session, after_sales_id: uuid.UUID, actor_id: uuid.UUID) -> AfterSalesOrder:
        after_sales = db.get(AfterSalesOrder, after_sales_id)
        if not after_sales:
            return None
        
        if after_sales.status == "completed":
            return after_sales
        if after_sales.status == "rejected":
            raise ValueError("Cannot complete a rejected after-sales order")

        # In a real system, reverse settlement would happen here.
        # For this MVP, we update the status and mark the order as refunded if it's a full return.
        
        after_sales.status = "completed"
        after_sales.completed_at = datetime.now(UTC)
        
        order = after_sales.order
        if after_sales.type == "return":
            order.status = "refunded"
            # Restore stock for returned items
            for line in order.lines:
                product = line.product
                product.stock += line.quantity
                db.add(product)

        # Write to audit log
        AuditService.write(
            db=db,
            actor_id=actor_id,
            action="reverse_settlement",
            target_type="after_sales_order",
            target_id=after_sales.id,
            metadata={
                "order_id": str(order.id),
                "refund_amount": str(after_sales.refund_amount),
                "type": after_sales.type
            }
        )
        
        db.commit()
        db.refresh(after_sales)
        return after_sales

    @staticmethod
    def get_request(db: Session, after_sales_id: uuid.UUID) -> AfterSalesOrder | None:
        return db.get(AfterSalesOrder, after_sales_id)
