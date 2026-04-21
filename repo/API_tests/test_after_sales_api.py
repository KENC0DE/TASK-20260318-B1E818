"""API tests for After-Sales endpoints."""

from __future__ import annotations

from fastapi.testclient import TestClient


def _create_settled_order(client: TestClient, admin_headers: dict[str, str], cashier_headers: dict[str, str]) -> str:
    # 1. Create product
    resp = client.post(
        "/products",
        json={
            "name": "AS Product",
            "barcode": "551001",
            "price": 80.0,
            "stock": 100,
        },
        headers=admin_headers,
    )
    product_id = resp.json()["id"]
    
    # 2. Create order
    order_resp = client.post(
        "/orders",
        json={"items": [{"product_id": product_id, "quantity": 1}]},
        headers=cashier_headers,
    )
    order_id = order_resp.json()["id"]
    
    # 3. Settle order
    client.post(
        f"/orders/{order_id}/payments",
        json={"payments": [{"method": "cash", "amount": 80.0}]},
        headers=cashier_headers,
    )
    return order_id


def test_create_after_sales_api_success(
    client: TestClient, admin_headers: dict[str, str], cashier_headers: dict[str, str]
) -> None:
    order_id = _create_settled_order(client, admin_headers, cashier_headers)
    
    response = client.post(
        "/after-sales",
        json={
            "original_order_id": order_id,
            "type": "return",
            "refund_amount": 80.0,
            "idempotency_key": "ikey-api-1",
            "reason": "Customer change of mind"
        },
        headers=cashier_headers,
    )
    
    assert response.status_code == 201
    assert response.json()["status"] == "pending"
    assert response.json()["idempotency_key"] == "ikey-api-1"


def test_after_sales_idempotency_api(
    client: TestClient, admin_headers: dict[str, str], cashier_headers: dict[str, str]
) -> None:
    order_id = _create_settled_order(client, admin_headers, cashier_headers)
    payload = {
        "original_order_id": order_id,
        "type": "return",
        "refund_amount": 40.0,
        "idempotency_key": "ikey-dup-api",
    }
    
    resp1 = client.post("/after-sales", json=payload, headers=cashier_headers)
    resp2 = client.post("/after-sales", json=payload, headers=cashier_headers)
    
    assert resp1.status_code == 201
    assert resp2.status_code == 201  # Service returns existing record
    assert resp1.json()["id"] == resp2.json()["id"]


def test_complete_after_sales_api(
    client: TestClient, admin_headers: dict[str, str], cashier_headers: dict[str, str]
) -> None:
    order_id = _create_settled_order(client, admin_headers, cashier_headers)
    
    as_resp = client.post(
        "/after-sales",
        json={
            "original_order_id": order_id,
            "type": "return",
            "refund_amount": 80.0,
            "idempotency_key": "ikey-api-comp",
        },
        headers=cashier_headers,
    )
    as_id = as_resp.json()["id"]
    
    comp_resp = client.post(f"/after-sales/{as_id}/complete", headers=admin_headers)
    assert comp_resp.status_code == 200
    assert comp_resp.json()["status"] == "completed"
    
    # Verify order status
    order_check = client.get(f"/orders/{order_id}", headers=cashier_headers)
    assert order_check.json()["status"] == "refunded"
