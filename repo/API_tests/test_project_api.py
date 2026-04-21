"""API tests for Project endpoints."""

from __future__ import annotations

import uuid
from fastapi.testclient import TestClient


def test_project_full_lifecycle_api(
    client: TestClient, 
    applicant_headers: dict[str, str], 
    reviewer_headers: dict[str, str]
) -> None:
    # 1. Create Project
    create_resp = client.post(
        "/projects",
        json={"title": "New Startup", "content": {"plan": "profit"}},
        headers=applicant_headers,
    )
    assert create_resp.status_code == 201
    project_id = create_resp.json()["id"]
    
    # 2. List Projects (Applicant view)
    list_resp = client.get("/projects", headers=applicant_headers)
    assert list_resp.status_code == 200
    assert list_resp.json()["total"] >= 1
    
    # 3. Get Details
    get_resp = client.get(f"/projects/{project_id}", headers=applicant_headers)
    assert get_resp.status_code == 200
    assert get_resp.json()["title"] == "New Startup"
    assert get_resp.json()["current_version_details"]["content"] == {"plan": "profit"}
    
    # 4. Update
    update_resp = client.put(
        f"/projects/{project_id}",
        json={"title": "Updated Startup"},
        headers=applicant_headers,
    )
    assert update_resp.status_code == 200
    assert update_resp.json()["title"] == "Updated Startup"
    
    # 5. Submit
    submit_resp = client.post(f"/projects/{project_id}/submit", headers=applicant_headers)
    assert submit_resp.status_code == 200
    assert submit_resp.json()["status"] == "submitted"
    
    # 6. Review (Reviewer view)
    review_resp = client.post(
        f"/projects/{project_id}/review",
        json={"decision": "approved", "comment": "Excellent plan"},
        headers=reviewer_headers,
    )
    assert review_resp.status_code == 200
    assert review_resp.json()["status"] == "approved"


def test_list_projects_reviewer(
    client: TestClient, 
    applicant_headers: dict[str, str], 
    reviewer_headers: dict[str, str]
) -> None:
    # Create a project as applicant
    client.post(
        "/projects",
        json={"title": "Reviewer List Test", "content": {}},
        headers=applicant_headers,
    )
    
    # List as reviewer should see all
    resp = client.get("/projects", headers=reviewer_headers)
    assert resp.status_code == 200
    assert any(p["title"] == "Reviewer List Test" for p in resp.json()["items"])


def test_get_project_unauthorized(
    client: TestClient, 
    applicant_headers: dict[str, str], 
    cashier_headers: dict[str, str]
) -> None:
    # Create project as applicant
    create_resp = client.post(
        "/projects",
        json={"title": "Secret Project", "content": {}},
        headers=applicant_headers,
    )
    project_id = create_resp.json()["id"]
    
    # Try get as cashier (role not allowed in endpoint)
    # Actually cashier is NOT allowed in require_role(APPLICANT, REVIEWER, ADMIN)
    resp = client.get(f"/projects/{project_id}", headers=cashier_headers)
    assert resp.status_code == 403
