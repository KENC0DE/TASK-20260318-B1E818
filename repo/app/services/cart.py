"""Cart session service."""

from __future__ import annotations

import uuid
from decimal import Decimal

from sqlalchemy.orm import Session

from app.models.cart import Cart, CartItem
from app.models.product import Product
from app.services.promotion import PromotionService


class CartService:
    @staticmethod
    def get_cart_or_404(db: Session, cart_id: uuid.UUID) -> Cart | None:
        return db.get(Cart, cart_id)

    @staticmethod
    def get_item(db: Session, cart_id: uuid.UUID, item_id: uuid.UUID) -> CartItem | None:
        return (
            db.query(CartItem)
            .filter(CartItem.id == item_id, CartItem.cart_id == cart_id)
            .first()
        )

    @staticmethod
    def find_item_by_product(db: Session, cart_id: uuid.UUID, product_id: uuid.UUID) -> CartItem | None:
        return (
            db.query(CartItem)
            .filter(CartItem.cart_id == cart_id, CartItem.product_id == product_id)
            .first()
        )

    @staticmethod
    def cart_items(db: Session, cart_id: uuid.UUID) -> list[tuple[CartItem, Product]]:
        return (
            db.query(CartItem, Product)
            .join(Product, Product.id == CartItem.product_id)
            .filter(CartItem.cart_id == cart_id)
            .order_by(CartItem.created_at.asc())
            .all()
        )

    @staticmethod
    def build_cart_projection(db: Session, cart: Cart) -> dict:
        item_rows = CartService.cart_items(db, cart.id)
        items = [row[0] for row in item_rows]
        active_rules = PromotionService.active_rules(db)
        evaluation = PromotionService.evaluate(items, active_rules)

        response_items = []
        for item, product in item_rows:
            response_items.append(
                {
                    "id": item.id,
                    "product_id": item.product_id,
                    "product_name": product.name,
                    "quantity": item.quantity,
                    "unit_price": item.unit_price,
                    "line_subtotal": item.unit_price * item.quantity,
                }
            )

        return {
            "id": cart.id,
            "status": cart.status,
            "created_by": cart.created_by,
            "items": response_items,
            "pricing": {
                "subtotal": evaluation.subtotal,
                "discount_total": evaluation.discount_total,
                "total": evaluation.total,
            },
            "applied_promotions": [
                {
                    "rule_id": item.rule_id,
                    "rule_name": item.rule_name,
                    "rule_type": item.rule_type,
                    "discount_amount": item.discount_amount,
                    "details": item.details,
                }
                for item in evaluation.applied_promotions
            ],
            "purchase_limit_violations": evaluation.purchase_limit_violations,
            "created_at": cart.created_at,
            "updated_at": cart.updated_at,
        }

    @staticmethod
    def create_cart(db: Session, created_by: uuid.UUID) -> Cart:
        cart = Cart(created_by=created_by, status="active")
        db.add(cart)
        db.commit()
        db.refresh(cart)
        return cart

    @staticmethod
    def add_item(db: Session, cart: Cart, product: Product, quantity: int) -> Cart:
        existing = CartService.find_item_by_product(db, cart.id, product.id)
        new_qty = quantity if existing is None else existing.quantity + quantity

        PromotionService.enforce_purchase_limit(db, product.id, new_qty)

        if existing is None:
            db.add(
                CartItem(
                    cart_id=cart.id,
                    product_id=product.id,
                    quantity=quantity,
                    unit_price=Decimal(str(product.price)),
                )
            )
        else:
            existing.quantity = new_qty
            db.add(existing)

        db.commit()
        db.refresh(cart)
        return cart
