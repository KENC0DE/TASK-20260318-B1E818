"""Cart session and cart item routes."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.auth import get_current_user, require_role
from app.db.session import get_db
from app.models.auth import User, UserRole
from app.models.product import Product
from app.schemas.cart import (
    CartCreateResponse,
    CartItemAddRequest,
    CartItemUpdateRequest,
    CartResponse,
)
from app.services.cart import CartService

router = APIRouter(prefix="/carts", tags=["Cart"])


@router.post("", response_model=CartCreateResponse, status_code=status.HTTP_201_CREATED)
def create_cart(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.CASHIER, UserRole.STORE_MANAGER, UserRole.ADMIN)),
) -> CartCreateResponse:
    cart = CartService.create_cart(db, current_user.id)
    return CartCreateResponse(id=cart.id, status=cart.status, created_at=cart.created_at)


@router.get("/{cart_id}", response_model=CartResponse)
def get_cart(
    cart_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CartResponse:
    cart = CartService.get_cart_or_404(db, cart_id)
    if cart is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cart not found")

    if current_user.role not in [UserRole.ADMIN, UserRole.STORE_MANAGER] and cart.created_by != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    return CartResponse.model_validate(CartService.build_cart_projection(db, cart))


@router.post("/{cart_id}/items", response_model=CartResponse)
def add_cart_item(
    cart_id: uuid.UUID,
    payload: CartItemAddRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CartResponse:
    cart = CartService.get_cart_or_404(db, cart_id)
    if cart is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cart not found")

    if current_user.role not in [UserRole.ADMIN, UserRole.STORE_MANAGER] and cart.created_by != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    product = db.get(Product, payload.product_id)
    if product is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    if not product.is_active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Product is inactive")

    try:
        cart = CartService.add_item(db, cart, product, payload.quantity)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    return CartResponse.model_validate(CartService.build_cart_projection(db, cart))


@router.put("/{cart_id}/items/{item_id}", response_model=CartResponse)
def update_cart_item(
    cart_id: uuid.UUID,
    item_id: uuid.UUID,
    payload: CartItemUpdateRequest,
    db: Session = Depends(get_db),
    _: User = Depends(require_role(UserRole.CASHIER, UserRole.STORE_MANAGER, UserRole.ADMIN)),
) -> CartResponse:
    cart = CartService.get_cart_or_404(db, cart_id)
    if cart is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cart not found")

    item = CartService.get_item(db, cart_id, item_id)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cart item not found")

    from app.services.promotion import PromotionService

    try:
        PromotionService.enforce_purchase_limit(db, item.product_id, payload.quantity)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    item.quantity = payload.quantity
    db.add(item)
    db.commit()
    db.refresh(cart)
    return CartResponse.model_validate(CartService.build_cart_projection(db, cart))


@router.delete("/{cart_id}/items/{item_id}", response_model=CartResponse)
def remove_cart_item(
    cart_id: uuid.UUID,
    item_id: uuid.UUID,
    db: Session = Depends(get_db),
    _: User = Depends(require_role(UserRole.CASHIER, UserRole.STORE_MANAGER, UserRole.ADMIN)),
) -> CartResponse:
    cart = CartService.get_cart_or_404(db, cart_id)
    if cart is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cart not found")

    item = CartService.get_item(db, cart_id, item_id)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cart item not found")

    db.delete(item)
    db.commit()
    db.refresh(cart)
    return CartResponse.model_validate(CartService.build_cart_projection(db, cart))
