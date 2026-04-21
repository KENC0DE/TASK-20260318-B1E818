from __future__ import annotations

from fastapi.testclient import TestClient


def _create_product(client: TestClient, headers: dict[str, str], barcode: str = "781000") -> str:
    response = client.post(
        "/products",
        json={
            "name": "Promo Product",
            "barcode": barcode,
            "internal_code": f"P-{barcode}",
            "pinyin_code": "promoproduct",
            "price": 20,
            "stock": 100,
            "is_active": True,
        },
        headers=headers,
    )
    assert response.status_code == 201
    return response.json()["id"]


def test_promotion_crud_lifecycle(client: TestClient, store_manager_headers: dict[str, str]) -> None:
    create_response = client.post(
        "/promotions",
        json={
            "name": "Spend100Save10",
            "rule_type": "spend_and_save",
            "priority": 10,
            "is_active": True,
            "config": {"threshold": 100, "discount": 10},
        },
        headers=store_manager_headers,
    )
    assert create_response.status_code == 201
    rule_id = create_response.json()["id"]

    list_response = client.get("/promotions", headers=store_manager_headers)
    assert list_response.status_code == 200
    assert list_response.json()["total"] >= 1

    update_response = client.put(
        f"/promotions/{rule_id}",
        json={"priority": 5},
        headers=store_manager_headers,
    )
    assert update_response.status_code == 200
    assert update_response.json()["priority"] == 5

    delete_response = client.delete(f"/promotions/{rule_id}", headers=store_manager_headers)
    assert delete_response.status_code == 204


def test_promotion_create_forbidden_for_cashier(
    client: TestClient, cashier_headers: dict[str, str]
) -> None:
    response = client.post(
        "/promotions",
        json={
            "name": "NoCashierCreate",
            "rule_type": "spend_and_save",
            "config": {"threshold": 100, "discount": 10},
        },
        headers=cashier_headers,
    )

    assert response.status_code == 403


def test_cart_add_item_and_apply_spend_save_promotion(
    client: TestClient,
    admin_headers: dict[str, str],
    cashier_headers: dict[str, str],
) -> None:
    product_id = _create_product(client, admin_headers, barcode="781100")

    promo_response = client.post(
        "/promotions",
        json={
            "name": "Spend100Save10",
            "rule_type": "spend_and_save",
            "priority": 10,
            "is_active": True,
            "config": {"threshold": 100, "discount": 10},
        },
        headers=admin_headers,
    )
    assert promo_response.status_code == 201

    cart_response = client.post("/carts", headers=cashier_headers)
    assert cart_response.status_code == 201
    cart_id = cart_response.json()["id"]

    add_response = client.post(
        f"/carts/{cart_id}/items",
        json={"product_id": product_id, "quantity": 6},
        headers=cashier_headers,
    )
    assert add_response.status_code == 200

    body = add_response.json()
    assert float(body["pricing"]["subtotal"]) == 120
    assert float(body["pricing"]["discount_total"]) == 10
    assert float(body["pricing"]["total"]) == 110
    assert len(body["applied_promotions"]) == 1


def test_cart_purchase_limit_enforced(
    client: TestClient,
    admin_headers: dict[str, str],
    cashier_headers: dict[str, str],
) -> None:
    product_id = _create_product(client, admin_headers, barcode="781200")

    promo_response = client.post(
        "/promotions",
        json={
            "name": "Limit2",
            "rule_type": "purchase_limit",
            "priority": 1,
            "is_active": True,
            "config": {"product_id": product_id, "max_qty": 2},
        },
        headers=admin_headers,
    )
    assert promo_response.status_code == 201

    cart_response = client.post("/carts", headers=cashier_headers)
    assert cart_response.status_code == 201
    cart_id = cart_response.json()["id"]

    first_add = client.post(
        f"/carts/{cart_id}/items",
        json={"product_id": product_id, "quantity": 2},
        headers=cashier_headers,
    )
    assert first_add.status_code == 200

    second_add = client.post(
        f"/carts/{cart_id}/items",
        json={"product_id": product_id, "quantity": 1},
        headers=cashier_headers,
    )
    assert second_add.status_code == 400
    assert "Purchase limit exceeded" in second_add.json()["detail"]


def test_cart_item_update_and_remove(client: TestClient, admin_headers: dict[str, str]) -> None:
    product_id = _create_product(client, admin_headers, barcode="781300")

    cart_response = client.post("/carts", headers=admin_headers)
    cart_id = cart_response.json()["id"]

    add_response = client.post(
        f"/carts/{cart_id}/items",
        json={"product_id": product_id, "quantity": 2},
        headers=admin_headers,
    )
    assert add_response.status_code == 200
    item_id = add_response.json()["items"][0]["id"]

    update_response = client.put(
        f"/carts/{cart_id}/items/{item_id}",
        json={"quantity": 5},
        headers=admin_headers,
    )
    assert update_response.status_code == 200
    assert update_response.json()["items"][0]["quantity"] == 5

    remove_response = client.delete(
        f"/carts/{cart_id}/items/{item_id}",
        headers=admin_headers,
    )
    assert remove_response.status_code == 200
    assert remove_response.json()["items"] == []
