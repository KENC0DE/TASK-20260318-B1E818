from __future__ import annotations

import uuid
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.models.auth import User, UserRole

def test_get_notifications_empty(client: TestClient, cashier_headers: dict[str, str]) -> None:
    response = client.get("/notifications", headers=cashier_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["items"] == []
    assert data["total"] == 0

def test_dispatch_and_get_notifications(client: TestClient, admin_headers: dict[str, str], cashier_headers: dict[str, str], db_session: Session) -> None:
    # 1. Get cashier user ID
    cashier = db_session.query(User).filter(User.username == "cashier").first()
    assert cashier is not None
    cashier_id = str(cashier.id)

    # 2. Dispatch notification
    payload = {
        "recipient_ids": [cashier_id],
        "event_type": "TEST_EVENT",
        "object_type": "PROJECT",
        "object_id": str(uuid.uuid4()),
        "message": "Hello Cashier"
    }
    dispatch_response = client.post("/notifications/dispatch", json=payload, headers=admin_headers)
    assert dispatch_response.status_code == 201
    assert len(dispatch_response.json()) == 1
    notification_id = dispatch_response.json()[0]["id"]

    # 3. Get notifications as cashier
    get_response = client.get("/notifications", headers=cashier_headers)
    assert get_response.status_code == 200
    data = get_response.json()
    assert data["total"] == 1
    assert data["items"][0]["message"] == "Hello Cashier"
    assert data["items"][0]["read_at"] is None

    # 4. Mark as read
    read_response = client.post(f"/notifications/{notification_id}/read", headers=cashier_headers)
    assert read_response.status_code == 200
    assert read_response.json()["read_at"] is not None

    # 5. Verify read status
    get_response_2 = client.get("/notifications", headers=cashier_headers)
    assert get_response_2.json()["items"][0]["read_at"] is not None

def test_dispatch_throttling(client: TestClient, admin_headers: dict[str, str], db_session: Session) -> None:
    cashier = db_session.query(User).filter(User.username == "cashier").first()
    cashier_id = str(cashier.id)
    obj_id = str(uuid.uuid4())

    payload = {
        "recipient_ids": [cashier_id],
        "event_type": "THROTTLE_EVENT",
        "object_id": obj_id,
        "message": "First"
    }
    # First dispatch
    r1 = client.post("/notifications/dispatch", json=payload, headers=admin_headers)
    assert r1.status_code == 201
    assert len(r1.json()) == 1

    # Second dispatch (throttled)
    payload["message"] = "Second"
    r2 = client.post("/notifications/dispatch", json=payload, headers=admin_headers)
    assert r2.status_code == 201
    assert len(r2.json()) == 0

def test_dispatch_admin_only(client: TestClient, cashier_headers: dict[str, str]) -> None:
    payload = {
        "recipient_ids": [str(uuid.uuid4())],
        "event_type": "TEST",
        "message": "TEST"
    }
    response = client.post("/notifications/dispatch", json=payload, headers=cashier_headers)
    assert response.status_code == 403
