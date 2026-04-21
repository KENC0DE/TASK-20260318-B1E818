"""API tests for Feature Library endpoints."""

from __future__ import annotations

import uuid
from fastapi.testclient import TestClient


def test_create_feature_definition_api(client: TestClient, admin_headers: dict[str, str]) -> None:
    payload = {
        "name": f"test_feature_{uuid.uuid4().hex[:6]}",
        "description": "A test feature",
        "data_type": "float",
        "ttl_seconds": 600,
        "computation_logic": {"type": "static"}
    }
    response = client.post("/features/definitions", json=payload, headers=admin_headers)
    assert response.status_code == 201
    assert response.json()["name"] == payload["name"]


def test_get_feature_definitions_api(client: TestClient, admin_headers: dict[str, str]) -> None:
    response = client.get("/features/definitions", headers=admin_headers)
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_compute_feature_api(client: TestClient, admin_headers: dict[str, str]) -> None:
    # 1. Create definition
    feat_name = f"compute_feat_{uuid.uuid4().hex[:6]}"
    client.post(
        "/features/definitions",
        json={
            "name": feat_name,
            "data_type": "float",
            "ttl_seconds": 600,
            "computation_logic": {"type": "correlation"}
        },
        headers=admin_headers
    )
    
    # 2. Compute
    payload = {
        "feature_name": feat_name,
        "entity_id": "user_api_test",
        "parameters": {}
    }
    response = client.post("/features/compute", json=payload, headers=admin_headers)
    assert response.status_code == 200
    assert response.json()["entity_id"] == "user_api_test"
    assert response.json()["value"] == 0.85


def test_get_feature_values_api(client: TestClient, admin_headers: dict[str, str]) -> None:
    response = client.get("/features/values", headers=admin_headers)
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_feature_permissions(client: TestClient, cashier_headers: dict[str, str]) -> None:
    # Cashiers should not be able to create definitions
    response = client.post(
        "/features/definitions",
        json={"name": "no_perm", "data_type": "int"},
        headers=cashier_headers
    )
    assert response.status_code == 403
