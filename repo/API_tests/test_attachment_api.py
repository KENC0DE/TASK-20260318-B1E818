"""API tests for Attachment endpoints."""

from __future__ import annotations

import io
import uuid
from fastapi.testclient import TestClient


def test_upload_and_retrieve_attachment_api(
    client: TestClient, 
    applicant_headers: dict[str, str]
) -> None:
    # 1. Upload
    file_content = b"fake pdf data"
    file = io.BytesIO(file_content)
    owner_id = str(uuid.uuid4())
    
    response = client.post(
        "/attachments",
        data={
            "owner_type": "project_version",
            "owner_id": owner_id,
        },
        files={
            "file": ("test.pdf", file, "application/pdf")
        },
        headers=applicant_headers,
    )
    
    assert response.status_code == 201
    att_id = response.json()["id"]
    assert response.json()["filename"] == "test.pdf"
    
    # 2. Get Metadata
    meta_resp = client.get(f"/attachments/{att_id}", headers=applicant_headers)
    assert meta_resp.status_code == 200
    assert meta_resp.json()["filename"] == "test.pdf"
    
    # 3. Download
    down_resp = client.get(f"/attachments/{att_id}/download", headers=applicant_headers)
    assert down_resp.status_code == 200
    assert down_resp.content == file_content
    assert "attachment; filename=\"test.pdf\"" in down_resp.headers["content-disposition"]


def test_get_attachment_not_found(
    client: TestClient, 
    applicant_headers: dict[str, str]
) -> None:
    fake_id = str(uuid.uuid4())
    resp = client.get(f"/attachments/{fake_id}", headers=applicant_headers)
    assert resp.status_code == 404

def test_attachment_object_level_auth(
    client: TestClient, 
    applicant_headers: dict[str, str],
    cashier_headers: dict[str, str],
    admin_headers: dict[str, str]
) -> None:
    # 1. Applicant uploads
    file_content = b"applicant pdf data"
    file = io.BytesIO(file_content)
    owner_id = str(uuid.uuid4())
    
    response = client.post(
        "/attachments",
        data={"owner_type": "project", "owner_id": owner_id},
        files={"file": ("applicant.pdf", file, "application/pdf")},
        headers=applicant_headers,
    )
    att_id = response.json()["id"]
    
    # 2. Cashier tries to access (should be 403)
    meta_resp = client.get(f"/attachments/{att_id}", headers=cashier_headers)
    assert meta_resp.status_code == 403
    
    down_resp = client.get(f"/attachments/{att_id}/download", headers=cashier_headers)
    assert down_resp.status_code == 403
    
    # 3. Admin can access (should be 200)
    admin_resp = client.get(f"/attachments/{att_id}", headers=admin_headers)
    assert admin_resp.status_code == 200
    assert admin_resp.json()["filename"] == "applicant.pdf"
