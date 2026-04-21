"""API tests for Order endpoints."""

from __future__ import annotations

from fastapi.testclient import TestClient


def _create_product(client: TestClient, admin_headers: dict[str, str]) -> str:
    resp = client.post(
        "/products",
        json={
            "name": "Order Test Product",
            "barcode": "881001",
            "price": 50.0,
            "stock": 100,
        },
        headers=admin_headers,
    )
    assert resp.status_code == 201
    return resp.json()["id"]


def test_create_order_from_items_success(
    client: TestClient, admin_headers: dict[str, str], cashier_headers: dict[str, str]
) -> None:
    product_id = _create_product(client, admin_headers)
    
    response = client.post(
        "/orders",
        json={
            "items": [{"product_id": product_id, "quantity": 3}],
            "apply_promotions": False
        },
        headers=cashier_headers,
    )
    
    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "pending"
    assert float(body["total"]) == 150.0
    assert len(body["lines"]) == 1


def test_get_order_and_receipt(
    client: TestClient, admin_headers: dict[str, str], cashier_headers: dict[str, str]
) -> None:
    product_id = _create_product(client, admin_headers)
    
    order_resp = client.post(
        "/orders",
        json={"items": [{"product_id": product_id, "quantity": 1}]},
        headers=cashier_headers,
    )
    order_id = order_resp.json()["id"]
    
    # Get order
    get_resp = client.get(f"/orders/{order_id}", headers=cashier_headers)
    assert get_resp.status_code == 200
    assert get_resp.json()["id"] == order_id
    
    # Get receipt
    receipt_resp = client.get(f"/orders/{order_id}/receipt", headers=cashier_headers)
    assert receipt_resp.status_code == 200
    assert receipt_resp.json()["order_id"] == order_id
    assert float(receipt_resp.json()["total"]) == 50.0


def test_void_order_by_manager(
    client: TestClient, admin_headers: dict[str, str], cashier_headers: dict[str, str]
) -> None:
    product_id = _create_product(client, admin_headers)
    order_resp = client.post(
        "/orders",
        json={"items": [{"product_id": product_id, "quantity": 1}]},
        headers=cashier_headers,
    )
    order_id = order_resp.json()["id"]
    
    # Try void as cashier (forbidden)
    void_cashier = client.post(f"/orders/{order_id}/void", headers=cashier_headers)
    assert void_cashier.status_code == 403
    
    # Void as admin
    void_admin = client.post(f"/orders/{order_id}/void", headers=admin_headers)
    assert void_admin.status_code == 200
    assert void_admin.json()["status"] == "voided"


def test_list_orders_filtering(
    client: TestClient, admin_headers: dict[str, str], cashier_headers: dict[str, str]
) -> None:
    # Ensure there's at least one order
    product_id = _create_product(client, admin_headers)
    client.post(
        "/orders",
        json={"items": [{"product_id": product_id, "quantity": 1}]},
        headers=cashier_headers,
    )
    
    resp = client.get("/orders", params={"status": "pending"}, headers=admin_headers)
    assert resp.status_code == 200
    assert resp.json()["total"] >= 1
    assert all(o["status"] == "pending" for o in resp.json()["items"])

def test_order_stock_enforcement(
    client: TestClient, admin_headers: dict[str, str], cashier_headers: dict[str, str]
) -> None:
    # 1. Create product with low stock
    resp = client.post(
        "/products",
        json={
            "name": "Low Stock Product",
            "barcode": "stock-001",
            "price": 10.0,
            "stock": 5,
        },
        headers=admin_headers,
    )
    product_id = resp.json()["id"]
    
    # 2. Try to order more than available (should fail)
    fail_resp = client.post(
        "/orders",
        json={"items": [{"product_id": product_id, "quantity": 10}]},
        headers=cashier_headers,
    )
    assert fail_resp.status_code == 400
    assert "Insufficient stock" in fail_resp.json()["detail"]
    
    # 3. Order within limit
    order_resp = client.post(
        "/orders",
        json={"items": [{"product_id": product_id, "quantity": 2}]},
        headers=cashier_headers,
    )
    assert order_resp.status_code == 201
    order_id = order_resp.json()["id"]
    
    # 4. Settle order and verify stock decrement
    client.post(
        f"/orders/{order_id}/payments",
        json={"payments": [{"method": "cash", "amount": 20.0}]},
        headers=cashier_headers,
    )
    
    # Check product stock
    # Note: we need to find the product again or have a GET /products/{id} endpoint
    # Since there is no direct GET /products/{id} in the list of implemented endpoints in README,
    # we can use search by barcode.
    search_resp = client.get(
        "/products/search",
        params={"q": "stock-001", "mode": "barcode"},
        headers=cashier_headers
    )
    assert search_resp.status_code == 200
    assert search_resp.json()["items"][0]["stock"] == 3
