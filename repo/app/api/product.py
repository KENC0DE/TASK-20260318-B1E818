"""Product API routes."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.auth import require_role
from app.db.session import get_db
from app.models.auth import User, UserRole
from app.models.product import Product
from app.schemas.product import (
    ProductCreateRequest,
    ProductResponse,
    ProductSearchMode,
    ProductSearchResponse,
    ProductUpdateRequest,
)
from app.services.product import ProductService

router = APIRouter(prefix="/products", tags=["Products"])


@router.get("/search", response_model=ProductSearchResponse)
def search_products(
    q: str = Query(min_length=1, max_length=256),
    mode: ProductSearchMode = ProductSearchMode.AUTO,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    _: User = Depends(require_role(UserRole.CASHIER, UserRole.STORE_MANAGER, UserRole.ADMIN)),
) -> ProductSearchResponse:
    items, total = ProductService.search(
        db=db,
        query_text=q,
        mode=mode,
        page=page,
        page_size=page_size,
    )
    return ProductSearchResponse(
        items=[ProductResponse.model_validate(item) for item in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post("", response_model=ProductResponse, status_code=status.HTTP_201_CREATED)
def create_product(
    payload: ProductCreateRequest,
    db: Session = Depends(get_db),
    _: User = Depends(require_role(UserRole.STORE_MANAGER, UserRole.ADMIN)),
) -> ProductResponse:
    product = Product(
        name=payload.name,
        barcode=payload.barcode.lower() if payload.barcode else None,
        internal_code=payload.internal_code.lower() if payload.internal_code else None,
        pinyin_code=ProductService.derive_pinyin_code(payload.name, payload.pinyin_code),
        price=payload.price,
        stock=payload.stock,
        is_active=payload.is_active,
    )
    db.add(product)

    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Product barcode or internal_code already exists",
        ) from exc

    db.refresh(product)
    return ProductResponse.model_validate(product)


@router.put("/{product_id}", response_model=ProductResponse)
def update_product(
    product_id: uuid.UUID,
    payload: ProductUpdateRequest,
    db: Session = Depends(get_db),
    _: User = Depends(require_role(UserRole.STORE_MANAGER, UserRole.ADMIN)),
) -> ProductResponse:
    product = db.get(Product, product_id)
    if product is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")

    update_data = payload.model_dump(exclude_unset=True)
    if not update_data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No fields provided for update")

    if "name" in update_data:
        product.name = update_data["name"]
    if "barcode" in update_data:
        product.barcode = update_data["barcode"].lower() if update_data["barcode"] else None
    if "internal_code" in update_data:
        product.internal_code = (
            update_data["internal_code"].lower() if update_data["internal_code"] else None
        )
    if "pinyin_code" in update_data:
        product.pinyin_code = ProductService.derive_pinyin_code(product.name, update_data["pinyin_code"])
    elif "name" in update_data:
        product.pinyin_code = ProductService.derive_pinyin_code(product.name, None)
    if "price" in update_data:
        product.price = update_data["price"]
    if "stock" in update_data:
        product.stock = update_data["stock"]
    if "is_active" in update_data:
        product.is_active = update_data["is_active"]

    db.add(product)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Product barcode or internal_code already exists",
        ) from exc

    db.refresh(product)
    return ProductResponse.model_validate(product)