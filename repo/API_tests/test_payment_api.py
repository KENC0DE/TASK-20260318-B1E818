"""API tests for Payment endpoints."""

from __future__ import annotations

from fastapi.testclient import TestClient


def _create_order(client: TestClient, admin_headers: dict[str, str], cashier_headers: dict[str, str]) -> str:
    # Create product
    resp = client.post(
        "/products",
        json={
            "name": "Payment Test Product",
            "barcode": "991001",
            "price": 120.0,
            "stock": 100,
        },
        headers=admin_headers,
    )
    product_id = resp.json()["id"]
    
    # Create order
    order_resp = client.post(
        "/orders",
        json={"items": [{"product_id": product_id, "quantity": 1}]},
        headers=cashier_headers,
    )
    return order_resp.json()["id"]


def test_record_single_payment_api_success(
    client: TestClient, admin_headers: dict[str, str], cashier_headers: dict[str, str]
) -> None:
    order_id = _create_order(client, admin_headers, cashier_headers)
    
    response = client.post(
        f"/orders/{order_id}/payments",
        json={"payments": [{"method": "cash", "amount": 120.0}]},
        headers=cashier_headers,
    )
    
    assert response.status_code == 200
    assert len(response.json()) == 1
    assert float(response.json()[0]["amount"]) == 120.0
    
    # Verify order is settled
    order_check = client.get(f"/orders/{order_id}", headers=cashier_headers)
    assert order_check.json()["status"] == "settled"


def test_record_split_payment_api_success(
    client: TestClient, admin_headers: dict[str, str], cashier_headers: dict[str, str]
) -> None:
    order_id = _create_order(client, admin_headers, cashier_headers)
    
    response = client.post(
        f"/orders/{order_id}/payments",
        json={
            "payments": [
                {"method": "cash", "amount": 50.0},
                {"method": "bank_card", "amount": 70.0}
            ]
        },
        headers=cashier_headers,
    )
    
    assert response.status_code == 200
    assert len(response.json()) == 2


def test_record_payment_mismatch_api_fails(
    client: TestClient, admin_headers: dict[str, str], cashier_headers: dict[str, str]
) -> None:
    order_id = _create_order(client, admin_headers, cashier_headers)
    
    response = client.post(
        f"/orders/{order_id}/payments",
        json={"payments": [{"method": "cash", "amount": 100.0}]},
        headers=cashier_headers,
    )
    
    assert response.status_code == 400
    assert "does not match order total" in response.json()["detail"]


def test_record_payment_on_settled_order_api_fails(
    client: TestClient, admin_headers: dict[str, str], cashier_headers: dict[str, str]
) -> None:
    order_id = _create_order(client, admin_headers, cashier_headers)
    
    # Settle first
    client.post(
        f"/orders/{order_id}/payments",
        json={"payments": [{"method": "cash", "amount": 120.0}]},
        headers=cashier_headers,
    )
    
    # Try settle again
    response = client.post(
        f"/orders/{order_id}/payments",
        json={"payments": [{"method": "cash", "amount": 120.0}]},
        headers=cashier_headers,
    )
    
    assert response.status_code == 409
    assert "already settled" in response.json()["detail"]
