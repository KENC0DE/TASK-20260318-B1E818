"""Product service logic."""

from __future__ import annotations

from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.models.product import Product
from app.schemas.product import ProductSearchMode


class ProductService:
    @staticmethod
    def derive_pinyin_code(name: str, pinyin_code: str | None) -> str:
        if pinyin_code:
            return pinyin_code.strip().lower()

        # Fallback keeps only alphanumeric chars as a lightweight searchable token.
        return "".join(ch for ch in name.strip().lower() if ch.isalnum())

    @staticmethod
    def search(
        db: Session,
        query_text: str,
        mode: ProductSearchMode,
        page: int,
        page_size: int,
    ) -> tuple[list[Product], int]:
        normalized_query = query_text.strip().lower()
        query = db.query(Product)

        if mode == ProductSearchMode.BARCODE:
            query = query.filter(func.lower(Product.barcode) == normalized_query)
        elif mode == ProductSearchMode.PINYIN:
            query = query.filter(Product.pinyin_code.ilike(f"{normalized_query}%"))
        elif mode == ProductSearchMode.INTERNAL_CODE:
            query = query.filter(func.lower(Product.internal_code) == normalized_query)
        else:
            query = query.filter(
                or_(
                    func.lower(Product.barcode) == normalized_query,
                    func.lower(Product.internal_code) == normalized_query,
                    Product.pinyin_code.ilike(f"{normalized_query}%"),
                )
            )

        total = query.count()
        items = (
            query.order_by(Product.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )
        return items, total