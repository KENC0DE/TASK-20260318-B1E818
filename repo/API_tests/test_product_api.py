from __future__ import annotations

from fastapi.testclient import TestClient


def test_create_product_admin_success(client: TestClient, admin_headers: dict[str, str]) -> None:
    response = client.post(
        "/products",
        json={
            "name": "Apple Juice",
            "barcode": "690001",
            "internal_code": "AJ-001",
            "pinyin_code": "pingguozhi",
            "price": 12.50,
            "stock": 20,
            "is_active": True,
        },
        headers=admin_headers,
    )

    assert response.status_code == 201
    body = response.json()
    assert body["name"] == "Apple Juice"
    assert body["barcode"] == "690001"


def test_create_product_forbidden_for_cashier(
    client: TestClient, cashier_headers: dict[str, str]
) -> None:
    response = client.post(
        "/products",
        json={
            "name": "Green Tea",
            "barcode": "690010",
            "internal_code": "GT-001",
            "price": 8.80,
            "stock": 10,
        },
        headers=cashier_headers,
    )

    assert response.status_code == 403


def test_search_by_barcode(client: TestClient, admin_headers: dict[str, str]) -> None:
    client.post(
        "/products",
        json={
            "name": "Soda",
            "barcode": "690100",
            "internal_code": "SD-001",
            "pinyin_code": "suda",
            "price": 3.20,
            "stock": 99,
        },
        headers=admin_headers,
    )

    search_response = client.get(
        "/products/search",
        params={"q": "690100", "mode": "barcode"},
        headers=admin_headers,
    )

    assert search_response.status_code == 200
    body = search_response.json()
    assert body["total"] == 1
    assert body["items"][0]["internal_code"] == "sd-001"


def test_search_by_pinyin_prefix(client: TestClient, admin_headers: dict[str, str]) -> None:
    client.post(
        "/products",
        json={
            "name": "Milk Tea",
            "barcode": "690200",
            "internal_code": "MT-001",
            "pinyin_code": "naicha",
            "price": 10.00,
            "stock": 15,
        },
        headers=admin_headers,
    )

    search_response = client.get(
        "/products/search",
        params={"q": "nai", "mode": "pinyin"},
        headers=admin_headers,
    )

    assert search_response.status_code == 200
    body = search_response.json()
    assert body["total"] == 1
    assert body["items"][0]["name"] == "Milk Tea"


def test_create_product_duplicate_barcode_conflict(
    client: TestClient, admin_headers: dict[str, str]
) -> None:
    payload = {
        "name": "Cola",
        "barcode": "699999",
        "internal_code": "CL-001",
        "price": 5.00,
        "stock": 10,
    }
    first = client.post("/products", json=payload, headers=admin_headers)
    assert first.status_code == 201

    second = client.post(
        "/products",
        json={
            "name": "Cola 2",
            "barcode": "699999",
            "internal_code": "CL-002",
            "price": 5.50,
            "stock": 8,
        },
        headers=admin_headers,
    )

    assert second.status_code == 409


def test_update_product_and_not_found(client: TestClient, admin_headers: dict[str, str]) -> None:
    create_response = client.post(
        "/products",
        json={
            "name": "Orange Juice",
            "barcode": "690300",
            "internal_code": "OJ-001",
            "price": 11.20,
            "stock": 12,
        },
        headers=admin_headers,
    )
    product_id = create_response.json()["id"]

    update_response = client.put(
        f"/products/{product_id}",
        json={"stock": 99, "price": 12.00},
        headers=admin_headers,
    )
    assert update_response.status_code == 200
    assert update_response.json()["stock"] == 99

    missing_update_response = client.put(
        "/products/00000000-0000-0000-0000-000000000000",
        json={"stock": 1},
        headers=admin_headers,
    )
    assert missing_update_response.status_code == 404