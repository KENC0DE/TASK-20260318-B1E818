"""API tests for Analytics endpoints."""

from __future__ import annotations

from datetime import date
from fastapi.testclient import TestClient


def test_get_daily_metrics_api(client: TestClient, admin_headers: dict[str, str]) -> None:
    response = client.get("/analytics/daily", headers=admin_headers)
    assert response.status_code == 200
    data = response.json()
    assert "transaction_volume" in data
    assert data["date"] == str(date.today())


def test_export_analytics_api(client: TestClient, admin_headers: dict[str, str]) -> None:
    response = client.get("/analytics/export", headers=admin_headers)
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    assert "date,transaction_volume" in response.text


def test_analytics_permissions(client: TestClient, cashier_headers: dict[str, str]) -> None:
    # Cashiers should not be able to access analytics
    response = client.get("/analytics/daily", headers=cashier_headers)
    assert response.status_code == 403
