from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

def test_create_config_admin_only(client: TestClient, cashier_headers: dict[str, str]) -> None:
    response = client.post(
        "/config",
        json={"config_key": "k", "config_value": {"v": 1}},
        headers=cashier_headers
    )
    assert response.status_code == 403

def test_config_lifecycle(client: TestClient, admin_headers: dict[str, str]) -> None:
    # Create v1
    resp = client.post(
        "/config",
        json={"config_key": "life", "config_value": {"v": 1}},
        headers=admin_headers
    )
    assert resp.status_code == 201
    assert resp.json()["version"] == 1

    # Create v2
    resp = client.post(
        "/config",
        json={"config_key": "life", "config_value": {"v": 2}},
        headers=admin_headers
    )
    assert resp.status_code == 201
    assert resp.json()["version"] == 2

    # Get active
    resp = client.get("/config/life", headers=admin_headers)
    assert resp.status_code == 200
    assert resp.json()["version"] == 2
    assert resp.json()["config_value"] == {"v": 2}

    # Get history
    resp = client.get("/config/life/history", headers=admin_headers)
    assert resp.status_code == 200
    assert len(resp.json()) == 2

    # Rollback
    resp = client.post("/config/life/rollback", headers=admin_headers)
    assert resp.status_code == 200
    assert resp.json()["version"] == 3
    assert resp.json()["config_value"] == {"v": 1}

def test_get_config_not_found(client: TestClient, admin_headers: dict[str, str]) -> None:
    resp = client.get("/config/nonexistent", headers=admin_headers)
    assert resp.status_code == 404

def test_config_rollout_logic(client: TestClient, admin_headers: dict[str, str], cashier_headers: dict[str, str]) -> None:
    # 1. Create config with 0% rollout
    client.post(
        "/config",
        json={"config_key": "rollout_test", "config_value": {"enabled": True}, "rollout_percentage": 0},
        headers=admin_headers
    )
    
    # 2. Get as cashier (should be 404/not found because 0% rollout)
    resp = client.get("/config/rollout_test", headers=cashier_headers)
    assert resp.status_code == 404
    
    # 3. Create config with 100% rollout
    client.post(
        "/config",
        json={"config_key": "rollout_test", "config_value": {"enabled": True}, "rollout_percentage": 100},
        headers=admin_headers
    )
    
    # 4. Get as cashier (should be 200)
    resp = client.get("/config/rollout_test", headers=cashier_headers)
    assert resp.status_code == 200
    assert resp.json()["config_value"] == {"enabled": True}
