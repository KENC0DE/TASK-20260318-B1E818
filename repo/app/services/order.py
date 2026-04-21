"""Order domain service."""

from __future__ import annotations

import uuid
from datetime import datetime, UTC, timedelta
from decimal import Decimal

from sqlalchemy import select, func, and_
from sqlalchemy.orm import Session, joinedload

from app.models.order import Order, OrderLine
from app.models.product import Product
from app.models.cart import Cart, CartItem
from app.services.promotion import PromotionService


class OrderService:
    @staticmethod
    def get_order_or_404(db: Session, order_id: uuid.UUID) -> Order | None:
        return (
            db.query(Order)
            .options(joinedload(Order.lines).joinedload(OrderLine.product))
            .filter(Order.id == order_id)
            .first()
        )

    @staticmethod
    def create_order(
        db: Session,
        cashier_id: uuid.UUID,
        items: list[dict] | None = None,
        cart_id: uuid.UUID | None = None,
        apply_promotions: bool = True,
    ) -> Order:
        order_items: list[CartItem] = []
        
        if cart_id:
            cart = db.get(Cart, cart_id)
            if not cart:
                raise ValueError("Cart not found")
            order_items = cart.items
        elif items:
            for item_data in items:
                product_id = uuid.UUID(str(item_data["product_id"]))
                quantity = int(item_data["quantity"])
                product = db.get(Product, product_id)
                if not product:
                    raise ValueError(f"Product {product_id} not found")
                if not product.is_active:
                    raise ValueError(f"Product {product_id} is inactive")
                if product.stock < quantity:
                    raise ValueError(f"Insufficient stock for product {product.name} (Available: {product.stock}, Requested: {quantity})")
                
                # Create a transient CartItem-like object for PromotionService
                order_items.append(
                    CartItem(
                        product_id=product.id,
                        quantity=quantity,
                        unit_price=Decimal(str(product.price))
                    )
                )
        else:
            raise ValueError("Either items or cart_id must be provided")

        if not order_items:
            raise ValueError("Order must have at least one item")

        # Evaluate promotions
        applied_promotions = []
        discount_total = Decimal("0")
        subtotal = sum((item.unit_price * item.quantity for item in order_items), Decimal("0"))
        
        if apply_promotions:
            active_rules = PromotionService.active_rules(db)
            evaluation = PromotionService.evaluate(order_items, active_rules)
            
            if evaluation.purchase_limit_violations:
                raise ValueError(f"Promotion violations: {', '.join(evaluation.purchase_limit_violations)}")
            
            discount_total = evaluation.discount_total
            applied_promotions = evaluation.applied_promotions

        # Create Order
        order = Order(
            cashier_id=cashier_id,
            status="pending",
            subtotal=subtotal,
            discount_total=discount_total,
            total=subtotal - discount_total,
        )
        db.add(order)
        db.flush()  # Get order ID

        # Create OrderLines
        # NOTE: Simple implementation: apply whole-order discount proportional to subtotal if it's a general discount,
        # or apply to specific lines if the promotion details indicate a product_id.
        # For MVP, we record the lines with their original prices and maybe store the total discount at order level.
        # But OrderLine has line_discount.
        
        # Prorate discount_total across all lines for simplicity in this POS
        # unless it's an item-specific discount from PromotionService.
        
        for item in order_items:
            line_subtotal = item.unit_price * item.quantity
            line_discount = Decimal("0")
            
            # Find item-specific discounts
            for ap in applied_promotions:
                if ap.details.get("product_id") == str(item.product_id):
                    line_discount += ap.discount_amount
            
            # If there's remaining discount_total that wasn't item-specific (like SPEND_AND_SAVE),
            # we don't necessarily have to prorate it to lines if the model doesn't require it to sum up perfectly.
            # But line_total should be line_subtotal - line_discount.
            
            order_line = OrderLine(
                order_id=order.id,
                product_id=item.product_id,
                quantity=item.quantity,
                unit_price=item.unit_price,
                line_discount=line_discount,
                line_total=line_subtotal - line_discount,
                # For simplicity, we only link one rule if multiple apply?
                # Usually we'd need a mapping table for multiple promotions per line.
                promotion_rule_id=applied_promotions[0].rule_id if applied_promotions else None
            )
            db.add(order_line)

        # Update receipt payload
        order.receipt_payload = OrderService.generate_receipt_payload(order)
        
        db.commit()
        db.refresh(order)
        return order

    @staticmethod
    def void_order(db: Session, order_id: uuid.UUID, cashier_id: uuid.UUID) -> Order:
        order = db.get(Order, order_id)
        if not order:
            return None
        if order.status != "pending":
            raise ValueError(f"Order cannot be voided in status: {order.status}")
        
        order.status = "voided"
        order.voided_at = datetime.now(UTC)
        db.commit()
        db.refresh(order)
        return order

    @staticmethod
    def list_orders(
        db: Session,
        status: str | None = None,
        from_date: datetime | None = None,
        to_date: datetime | None = None,
        page: int = 1,
        page_size: int = 20
    ) -> tuple[list[Order], int]:
        query = db.query(Order)
        if status:
            query = query.filter(Order.status == status)
        if from_date:
            query = query.filter(Order.created_at >= from_date)
        if to_date:
            query = query.filter(Order.created_at <= to_date)
            
        total = query.count()
        items = query.order_by(Order.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()
        return items, total

    @staticmethod
    def auto_void_pending_orders(db: Session) -> int:
        threshold = datetime.now(UTC) - timedelta(minutes=30)
        orders_to_void = (
            db.query(Order)
            .filter(Order.status == "pending", Order.created_at < threshold)
            .all()
        )
        for order in orders_to_void:
            order.status = "voided"
            order.voided_at = datetime.now(UTC)
        
        db.commit()
        return len(orders_to_void)

    @staticmethod
    def generate_receipt_payload(order: Order) -> dict:
        lines = []
        for line in order.lines:
            lines.append({
                "product_id": str(line.product_id),
                "product_name": line.product.name if line.product else "Unknown",
                "quantity": line.quantity,
                "unit_price": str(line.unit_price),
                "line_total": str(line.line_total),
                "line_discount": str(line.line_discount),
            })
            
        return {
            "order_id": str(order.id),
            "subtotal": str(order.subtotal),
            "discount_total": str(order.discount_total),
            "total": str(order.total),
            "status": order.status,
            "lines": lines,
            "cashier_id": str(order.cashier_id),
            "issued_at": order.created_at.isoformat() if order.created_at else datetime.now(UTC).isoformat(),
        }
