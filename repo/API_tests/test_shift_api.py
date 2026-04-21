from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.models.audit import AuditLog

def test_shift_open_success(client: TestClient, cashier_headers: dict[str, str], db_session: Session) -> None:
    response = client.post("/shifts/open", headers=cashier_headers)
    assert response.status_code == 200
    assert response.json() == {"message": "Shift opened"}

    # Verify audit log
    audit = db_session.query(AuditLog).filter(AuditLog.action == "shift_open").first()
    assert audit is not None
    assert audit.target_type == "shift"

def test_shift_close_success(client: TestClient, cashier_headers: dict[str, str], db_session: Session) -> None:
    response = client.post("/shifts/close", headers=cashier_headers)
    assert response.status_code == 200
    assert response.json() == {"message": "Shift closed"}

    # Verify audit log
    audit = db_session.query(AuditLog).filter(AuditLog.action == "shift_close").first()
    assert audit is not None
    assert audit.target_type == "shift"

def test_shift_endpoints_require_auth(client: TestClient) -> None:
    response = client.post("/shifts/open")
    assert response.status_code == 401

    response = client.post("/shifts/close")
    assert response.status_code == 401
