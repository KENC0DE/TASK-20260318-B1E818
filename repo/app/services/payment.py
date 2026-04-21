"""Payment domain service."""

from __future__ import annotations

import uuid
from datetime import datetime, UTC
from decimal import Decimal

from sqlalchemy.orm import Session

from app.models.order import Order
from app.models.payment import PaymentRecord
from app.core.audit import AuditService


class PaymentService:
    @staticmethod
    def record_payments(
        db: Session,
        order_id: uuid.UUID,
        payments: list[dict],
        cashier_id: uuid.UUID
    ) -> list[PaymentRecord]:
        order = db.get(Order, order_id)
        if not order:
            raise ValueError("Order not found")
            
        if order.status == "settled":
            raise ValueError("Order already settled")
        if order.status == "voided":
            raise ValueError("Order is voided")

        payment_total = sum((Decimal(str(p["amount"])) for p in payments), Decimal("0"))
        
        # Validate sum = order total
        if abs(payment_total - order.total) > Decimal("0.001"):
            raise ValueError(f"Payment total {payment_total} does not match order total {order.total}")

        records = []
        for p_data in payments:
            record = PaymentRecord(
                order_id=order.id,
                method=p_data["method"],
                amount=Decimal(str(p_data["amount"]))
            )
            db.add(record)
            records.append(record)

        # Transition order to SETTLED
        order.status = "settled"
        order.settled_at = datetime.now(UTC)

        # Decrement stock
        for line in order.lines:
            product = line.product
            if product.stock < line.quantity:
                raise ValueError(f"Insufficient stock for {product.name} at time of settlement")
            product.stock -= line.quantity
            db.add(product)
        
        # Write to audit log
        AuditService.write(
            db=db,
            actor_id=cashier_id,
            action="payment_recorded",
            target_type="order",
            target_id=order.id,
            metadata={"total": str(order.total), "methods": [p["method"] for p in payments]}
        )
        
        db.commit()
        for r in records:
            db.refresh(r)
        return records
