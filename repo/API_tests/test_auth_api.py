from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.auth import User, UserRole


def test_login_success_returns_token(client: TestClient) -> None:
    response = client.post(
        "/auth/login",
        json={"username": "admin", "password": "adminpass123"},
    )

    assert response.status_code == 200
    body = response.json()
    assert "access_token" in body
    assert body["token_type"] == "bearer"
    assert body["expires_in"] > 0


def test_login_locks_after_five_failures(client: TestClient, db_session: Session) -> None:
    for _ in range(5):
        response = client.post(
            "/auth/login",
            json={"username": "cashier", "password": "wrong-password"},
        )

    assert response.status_code == 423
    payload = response.json()["detail"]
    assert payload["retry_after_seconds"] > 0

    user = db_session.query(User).filter(User.username == "cashier").first()
    assert user is not None
    assert user.role == UserRole.CASHIER
    assert user.locked_until is not None


def test_create_user_admin_only(client: TestClient, cashier_headers: dict[str, str]) -> None:
    response = client.post(
        "/auth/users",
        json={"username": "new-user", "password": "password123", "role": "cashier"},
        headers=cashier_headers,
    )

    assert response.status_code == 403


def test_create_user_and_get_profile(client: TestClient, admin_headers: dict[str, str]) -> None:
    create_response = client.post(
        "/auth/users",
        json={
            "username": "new-admin-created",
            "password": "password123",
            "role": "reviewer",
            "email": "reviewer@example.com",
            "contact": "123-456",
        },
        headers=admin_headers,
    )
    assert create_response.status_code == 201

    user_id = create_response.json()["id"]
    profile_response = client.get(f"/auth/users/{user_id}", headers=admin_headers)

    assert profile_response.status_code == 200
    profile_body = profile_response.json()
    assert profile_body["username"] == "new-admin-created"
    assert profile_body["role"] == "reviewer"
    assert profile_body["email"] == "reviewer@example.com"


def test_update_user_role(client: TestClient, admin_headers: dict[str, str]) -> None:
    create_response = client.post(
        "/auth/users",
        json={"username": "editable-role", "password": "password123", "role": "cashier"},
        headers=admin_headers,
    )
    user_id = create_response.json()["id"]

    update_response = client.put(
        f"/auth/users/{user_id}/role",
        json={"role": "store_manager"},
        headers=admin_headers,
    )

    assert update_response.status_code == 200
    assert update_response.json()["role"] == "store_manager"
