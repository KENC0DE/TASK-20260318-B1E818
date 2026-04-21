from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.product import Product
from app.schemas.product import ProductSearchMode
from app.services.product import ProductService


def _seed_products(db_session: Session) -> None:
    db_session.add_all(
        [
            Product(
                name="Apple Juice",
                barcode="690001",
                internal_code="AJ-001",
                pinyin_code="pingguozhi",
                price=12.50,
                stock=20,
                is_active=True,
            ),
            Product(
                name="Green Tea",
                barcode="690002",
                internal_code="GT-001",
                pinyin_code="lvcha",
                price=8.80,
                stock=30,
                is_active=True,
            ),
        ]
    )
    db_session.commit()


def test_derive_pinyin_code_fallback() -> None:
    code = ProductService.derive_pinyin_code("Green Tea", None)

    assert code == "greentea"


def test_search_by_barcode_mode(db_session: Session) -> None:
    _seed_products(db_session)

    items, total = ProductService.search(db_session, "690001", ProductSearchMode.BARCODE, 1, 20)

    assert total == 1
    assert items[0].name == "Apple Juice"


def test_search_by_pinyin_prefix_mode(db_session: Session) -> None:
    _seed_products(db_session)

    items, total = ProductService.search(db_session, "lv", ProductSearchMode.PINYIN, 1, 20)

    assert total == 1
    assert items[0].name == "Green Tea"


def test_search_auto_mode_matches_internal_code(db_session: Session) -> None:
    _seed_products(db_session)

    items, total = ProductService.search(db_session, "gt-001", ProductSearchMode.AUTO, 1, 20)

    assert total == 1
    assert items[0].barcode == "690002"