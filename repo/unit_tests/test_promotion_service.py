from __future__ import annotations

import uuid
from decimal import Decimal

import pytest

from app.models.cart import CartItem
from app.models.promotion import PromotionRule, PromotionRuleType
from app.services.promotion import PromotionService


def _rule(rule_type: PromotionRuleType, config: dict, name: str = "rule") -> PromotionRule:
    return PromotionRule(
        id=uuid.uuid4(),
        name=name,
        rule_type=rule_type,
        priority=1,
        is_active=True,
        config_json=config,
    )


def _item(product_id: uuid.UUID, qty: int, unit_price: Decimal) -> CartItem:
    return CartItem(
        id=uuid.uuid4(),
        cart_id=uuid.uuid4(),
        product_id=product_id,
        quantity=qty,
        unit_price=unit_price,
    )


def test_validate_config_rejects_invalid_spend_and_save() -> None:
    with pytest.raises(ValueError):
        PromotionService.validate_config(
            PromotionRuleType.SPEND_AND_SAVE,
            {"threshold": 0, "discount": 10},
        )


def test_evaluate_spend_and_save_discount() -> None:
    items = [_item(uuid.uuid4(), 3, Decimal("40"))]
    rules = [
        _rule(
            PromotionRuleType.SPEND_AND_SAVE,
            {"threshold": "100", "discount": "10"},
            name="Spend100Save10",
        )
    ]

    result = PromotionService.evaluate(items, rules)

    assert result.subtotal == Decimal("120")
    assert result.discount_total == Decimal("10")
    assert result.total == Decimal("110")
    assert len(result.applied_promotions) == 1


def test_evaluate_buy_and_get_for_specific_product() -> None:
    product_id = uuid.uuid4()
    items = [_item(product_id, 6, Decimal("5"))]
    rules = [
        _rule(
            PromotionRuleType.BUY_AND_GET,
            {"product_id": str(product_id), "buy_qty": 2, "free_qty": 1},
            name="Buy2Get1",
        )
    ]

    result = PromotionService.evaluate(items, rules)

    assert result.subtotal == Decimal("30")
    assert result.discount_total == Decimal("10")
    assert result.total == Decimal("20")


def test_evaluate_tiered_pricing_discount() -> None:
    product_id = uuid.uuid4()
    items = [_item(product_id, 5, Decimal("10"))]
    rules = [
        _rule(
            PromotionRuleType.TIERED_PRICING,
            {
                "product_id": str(product_id),
                "tiers": [
                    {"min_qty": 3, "unit_price": "9"},
                    {"min_qty": 5, "unit_price": "8.5"},
                ],
            },
            name="TieredTea",
        )
    ]

    result = PromotionService.evaluate(items, rules)

    assert result.subtotal == Decimal("50")
    assert result.discount_total == Decimal("7.5")
    assert result.total == Decimal("42.5")


def test_evaluate_purchase_limit_violation() -> None:
    product_id = uuid.uuid4()
    items = [_item(product_id, 6, Decimal("2"))]
    rules = [
        _rule(
            PromotionRuleType.PURCHASE_LIMIT,
            {"product_id": str(product_id), "max_qty": 5},
            name="Limit5",
        )
    ]

    result = PromotionService.evaluate(items, rules)

    assert result.discount_total == Decimal("0")
    assert len(result.purchase_limit_violations) == 1
