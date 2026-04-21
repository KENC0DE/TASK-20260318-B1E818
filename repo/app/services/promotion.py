"""Promotion rule validation and evaluation service."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import and_, or_
from sqlalchemy.orm import Session

from app.models.cart import CartItem
from app.models.promotion import PromotionRule, PromotionRuleType


@dataclass
class AppliedPromotion:
    rule_id: uuid.UUID
    rule_name: str
    rule_type: str
    discount_amount: Decimal
    details: dict


@dataclass
class PromotionEvaluationResult:
    subtotal: Decimal
    discount_total: Decimal
    total: Decimal
    applied_promotions: list[AppliedPromotion]
    purchase_limit_violations: list[str]


class PromotionService:
    @staticmethod
    def validate_time_window(start_at: datetime | None, end_at: datetime | None) -> None:
        if start_at and end_at and end_at < start_at:
            raise ValueError("end_at must be later than start_at")

    @staticmethod
    def validate_config(rule_type: PromotionRuleType, config: dict) -> dict:
        if not isinstance(config, dict):
            raise ValueError("config must be an object")

        if rule_type == PromotionRuleType.SPEND_AND_SAVE:
            threshold = Decimal(str(config.get("threshold", 0)))
            discount = Decimal(str(config.get("discount", 0)))
            if threshold <= 0 or discount <= 0:
                raise ValueError("spend_and_save requires positive threshold and discount")
            return {"threshold": str(threshold), "discount": str(discount)}

        if rule_type == PromotionRuleType.BUY_AND_GET:
            buy_qty = int(config.get("buy_qty", 0))
            free_qty = int(config.get("free_qty", 0))
            if buy_qty <= 0 or free_qty <= 0:
                raise ValueError("buy_and_get requires buy_qty and free_qty greater than 0")

            normalized = {"buy_qty": buy_qty, "free_qty": free_qty}
            product_id = config.get("product_id")
            if product_id is not None:
                normalized["product_id"] = str(uuid.UUID(str(product_id)))
            return normalized

        if rule_type == PromotionRuleType.TIERED_PRICING:
            product_id = config.get("product_id")
            tiers = config.get("tiers")
            if not product_id:
                raise ValueError("tiered_pricing requires product_id")
            if not isinstance(tiers, list) or not tiers:
                raise ValueError("tiered_pricing requires non-empty tiers")

            normalized_tiers: list[dict] = []
            for tier in tiers:
                min_qty = int(tier.get("min_qty", 0))
                unit_price = Decimal(str(tier.get("unit_price", 0)))
                if min_qty <= 0 or unit_price <= 0:
                    raise ValueError("each tier requires min_qty > 0 and unit_price > 0")
                normalized_tiers.append({"min_qty": min_qty, "unit_price": str(unit_price)})

            normalized_tiers.sort(key=lambda t: t["min_qty"])
            return {"product_id": str(uuid.UUID(str(product_id))), "tiers": normalized_tiers}

        if rule_type == PromotionRuleType.PURCHASE_LIMIT:
            product_id = config.get("product_id")
            max_qty = int(config.get("max_qty", 0))
            if not product_id or max_qty <= 0:
                raise ValueError("purchase_limit requires product_id and max_qty > 0")
            return {"product_id": str(uuid.UUID(str(product_id))), "max_qty": max_qty}

        raise ValueError("Unsupported promotion rule type")

    @staticmethod
    def active_rules(db: Session) -> list[PromotionRule]:
        now = datetime.now(UTC)
        return (
            db.query(PromotionRule)
            .filter(PromotionRule.is_active.is_(True))
            .filter(
                and_(
                    or_(PromotionRule.start_at.is_(None), PromotionRule.start_at <= now),
                    or_(PromotionRule.end_at.is_(None), PromotionRule.end_at >= now),
                )
            )
            .order_by(PromotionRule.priority.asc(), PromotionRule.created_at.asc())
            .all()
        )

    @staticmethod
    def enforce_purchase_limit(
        db: Session,
        product_id: uuid.UUID,
        requested_qty: int,
    ) -> None:
        active_purchase_limits = [
            rule
            for rule in PromotionService.active_rules(db)
            if rule.rule_type == PromotionRuleType.PURCHASE_LIMIT
            and str(rule.config_json.get("product_id")) == str(product_id)
        ]

        if not active_purchase_limits:
            return

        max_qty = min(int(rule.config_json["max_qty"]) for rule in active_purchase_limits)
        if requested_qty > max_qty:
            raise ValueError(f"Purchase limit exceeded: maximum quantity is {max_qty}")

    @staticmethod
    def evaluate(items: list[CartItem], rules: list[PromotionRule]) -> PromotionEvaluationResult:
        subtotal = sum((item.unit_price * item.quantity for item in items), Decimal("0"))
        discount_total = Decimal("0")
        applied: list[AppliedPromotion] = []
        violations: list[str] = []

        qty_by_product: dict[str, int] = {}
        unit_price_by_product: dict[str, Decimal] = {}
        for item in items:
            key = str(item.product_id)
            qty_by_product[key] = qty_by_product.get(key, 0) + item.quantity
            unit_price_by_product[key] = item.unit_price

        for rule in rules:
            cfg = rule.config_json
            discount = Decimal("0")
            details: dict = {}

            if rule.rule_type == PromotionRuleType.SPEND_AND_SAVE:
                threshold = Decimal(str(cfg["threshold"]))
                amount = Decimal(str(cfg["discount"]))
                times = int(subtotal // threshold)
                if times > 0:
                    discount = amount * times
                    details = {"times": times, "threshold": str(threshold), "discount": str(amount)}

            elif rule.rule_type == PromotionRuleType.BUY_AND_GET:
                buy_qty = int(cfg["buy_qty"])
                free_qty = int(cfg["free_qty"])
                product_id = cfg.get("product_id")

                if product_id:
                    qty = qty_by_product.get(str(product_id), 0)
                    if qty > 0:
                        sets = qty // (buy_qty + free_qty)
                        free_units = sets * free_qty
                        if free_units > 0:
                            discount = unit_price_by_product[str(product_id)] * free_units
                            details = {"product_id": product_id, "free_units": free_units}
                elif items:
                    total_qty = sum(item.quantity for item in items)
                    sets = total_qty // (buy_qty + free_qty)
                    free_units = sets * free_qty
                    if free_units > 0:
                        cheapest = min(item.unit_price for item in items)
                        discount = cheapest * free_units
                        details = {"free_units": free_units}

            elif rule.rule_type == PromotionRuleType.TIERED_PRICING:
                product_id = str(cfg["product_id"])
                qty = qty_by_product.get(product_id, 0)
                if qty > 0:
                    best_price: Decimal | None = None
                    for tier in cfg["tiers"]:
                        if qty >= int(tier["min_qty"]):
                            best_price = Decimal(str(tier["unit_price"]))
                    if best_price is not None:
                        original = unit_price_by_product[product_id]
                        if original > best_price:
                            discount = (original - best_price) * qty
                            details = {"product_id": product_id, "tier_price": str(best_price), "qty": qty}

            elif rule.rule_type == PromotionRuleType.PURCHASE_LIMIT:
                product_id = str(cfg["product_id"])
                max_qty = int(cfg["max_qty"])
                qty = qty_by_product.get(product_id, 0)
                if qty > max_qty:
                    violations.append(
                        f"Product {product_id} exceeds purchase limit {max_qty} with quantity {qty}"
                    )

            if discount > 0:
                discount_total += discount
                applied.append(
                    AppliedPromotion(
                        rule_id=rule.id,
                        rule_name=rule.name,
                        rule_type=rule.rule_type.value,
                        discount_amount=discount,
                        details=details,
                    )
                )

        if discount_total > subtotal:
            discount_total = subtotal

        total = subtotal - discount_total
        return PromotionEvaluationResult(
            subtotal=subtotal,
            discount_total=discount_total,
            total=total,
            applied_promotions=applied,
            purchase_limit_violations=violations,
        )
