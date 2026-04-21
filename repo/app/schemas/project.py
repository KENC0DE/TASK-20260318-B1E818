"""Project pydantic schemas."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class ProjectVersionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    project_id: uuid.UUID
    version_number: int
    content: dict[str, Any]
    diff_summary: str | None = None
    submitted_at: datetime | None = None
    reviewer_id: uuid.UUID | None = None
    review_comment: str | None = None
    review_status: str


class ProjectResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    applicant_id: uuid.UUID
    title: str
    status: str
    current_version: int
    created_at: datetime
    updated_at: datetime
    current_version_details: ProjectVersionResponse | None = None


class ProjectCreateRequest(BaseModel):
    title: str
    content: dict[str, Any]


class ProjectUpdateRequest(BaseModel):
    title: str | None = None
    content: dict[str, Any] | None = None


class ProjectReviewRequest(BaseModel):
    decision: str  # approved / rejected
    comment: str | None = None


class ProjectListResponse(BaseModel):
    items: list[ProjectResponse]
    total: int
    page: int
    page_size: int
