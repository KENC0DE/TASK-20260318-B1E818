"""Project API routes."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.core.auth import require_role
from app.db.session import get_db
from app.models.auth import User, UserRole
from app.schemas.project import (
    ProjectCreateRequest,
    ProjectResponse,
    ProjectUpdateRequest,
    ProjectReviewRequest,
    ProjectListResponse,
    ProjectVersionResponse
)
from app.services.project import ProjectService

router = APIRouter(prefix="/projects", tags=["Projects"])


@router.post("", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
def create_project(
    payload: ProjectCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.APPLICANT)),
) -> ProjectResponse:
    project = ProjectService.create_project(
        db=db,
        applicant_id=current_user.id,
        title=payload.title,
        content=payload.content
    )
    return ProjectResponse.model_validate(project)


@router.get("", response_model=ProjectListResponse)
def list_projects(
    status: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.APPLICANT, UserRole.REVIEWER, UserRole.ADMIN)),
) -> ProjectListResponse:
    applicant_id = None
    if current_user.role == UserRole.APPLICANT:
        applicant_id = current_user.id
        
    items, total = ProjectService.list_projects(
        db=db,
        applicant_id=applicant_id,
        status=status,
        page=page,
        page_size=page_size
    )
    return ProjectListResponse(
        items=[ProjectResponse.model_validate(item) for item in items],
        total=total,
        page=page,
        page_size=page_size
    )


@router.get("/{project_id}", response_model=ProjectResponse)
def get_project(
    project_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.APPLICANT, UserRole.REVIEWER, UserRole.ADMIN)),
) -> ProjectResponse:
    project = ProjectService.get_project_details(db, project_id)
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    
    if current_user.role == UserRole.APPLICANT and project.applicant_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to view this project")

    # Include latest version details in the response
    latest_version = project.versions[0] if project.versions else None
    response = ProjectResponse.model_validate(project)
    if latest_version:
        response.current_version_details = ProjectVersionResponse.model_validate(latest_version)
    return response


@router.put("/{project_id}", response_model=ProjectResponse)
def update_project(
    project_id: uuid.UUID,
    payload: ProjectUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.APPLICANT)),
) -> ProjectResponse:
    try:
        project = ProjectService.update_project(
            db=db,
            project_id=project_id,
            user_id=current_user.id,
            title=payload.title,
            content=payload.content
        )
        if not project:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
        return ProjectResponse.model_validate(project)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))


@router.post("/{project_id}/submit", response_model=ProjectResponse)
def submit_project(
    project_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.APPLICANT)),
) -> ProjectResponse:
    try:
        project = ProjectService.submit_project(db, project_id, current_user.id)
        if not project:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
        return ProjectResponse.model_validate(project)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.post("/{project_id}/review", response_model=ProjectResponse)
def review_project(
    project_id: uuid.UUID,
    payload: ProjectReviewRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.REVIEWER, UserRole.ADMIN)),
) -> ProjectResponse:
    try:
        project = ProjectService.review_project(
            db=db,
            project_id=project_id,
            reviewer_id=current_user.id,
            decision=payload.decision,
            comment=payload.comment
        )
        if not project:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
        return ProjectResponse.model_validate(project)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.post("/{project_id}/deactivate", response_model=ProjectResponse)
def deactivate_project(
    project_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.APPLICANT, UserRole.ADMIN)),
) -> ProjectResponse:
    try:
        project = ProjectService.deactivate_project(
            db=db,
            project_id=project_id,
            user_id=current_user.id,
            is_admin=current_user.role == UserRole.ADMIN
        )
        if not project:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
        return ProjectResponse.model_validate(project)
    except ValueError as exc:
        if "authorized" in str(exc):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
