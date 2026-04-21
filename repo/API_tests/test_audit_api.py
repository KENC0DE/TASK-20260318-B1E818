from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
import uuid

from app.core.audit import AuditService
from app.models.auth import User, UserRole

def test_get_audit_logs_admin_only(client: TestClient, cashier_headers: dict[str, str]) -> None:
    response = client.get("/audit-logs", headers=cashier_headers)
    assert response.status_code == 403

def test_get_audit_logs_success(client: TestClient, admin_headers: dict[str, str], db_session: Session) -> None:
    # Ensure there is at least one audit log entry
    AuditService.write(db_session, action="test_action", target_type="test_target")
    db_session.commit()

    response = client.get("/audit-logs", headers=admin_headers)
    assert response.status_code == 200
    body = response.json()
    assert "items" in body
    assert "total" in body
    assert len(body["items"]) >= 1

def test_get_audit_logs_filtering(client: TestClient, admin_headers: dict[str, str], db_session: Session) -> None:
    actor_id = uuid.uuid4()
    AuditService.write(db_session, action="filtered_action", actor_id=actor_id, target_type="type1")
    AuditService.write(db_session, action="other_action", target_type="type2")
    db_session.commit()

    # Filter by action
    response = client.get("/audit-logs?action=filtered_action", headers=admin_headers)
    assert response.status_code == 200
    items = response.json()["items"]
    assert all(item["action"] == "filtered_action" for item in items)
    assert len(items) >= 1

    # Filter by actor_id
    response = client.get(f"/audit-logs?actor_id={actor_id}", headers=admin_headers)
    assert response.status_code == 200
    items = response.json()["items"]
    assert all(item["actor_id"] == str(actor_id) for item in items)
    assert len(items) >= 1

    # Filter by target_type
    response = client.get("/audit-logs?target_type=type2", headers=admin_headers)
    assert response.status_code == 200
    items = response.json()["items"]
    assert all(item["target_type"] == "type2" for item in items)
    assert len(items) >= 1
