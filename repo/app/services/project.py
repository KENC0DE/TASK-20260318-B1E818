"""Project domain service."""

from __future__ import annotations

import uuid
import json
from datetime import datetime, UTC
from typing import Any

from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.models.project import Project, ProjectVersion


class ProjectService:
    @staticmethod
    def create_project(db: Session, applicant_id: uuid.UUID, title: str, content: dict[str, Any]) -> Project:
        project = Project(
            applicant_id=applicant_id,
            title=title,
            status="draft",
            current_version=1
        )
        db.add(project)
        db.flush()

        version = ProjectVersion(
            project_id=project.id,
            version_number=1,
            content=content,
            review_status="pending"
        )
        db.add(version)
        db.commit()
        db.refresh(project)
        return project

    @staticmethod
    def update_project(db: Session, project_id: uuid.UUID, user_id: uuid.UUID, title: str | None, content: dict[str, Any] | None) -> Project:
        project = db.get(Project, project_id)
        if not project:
            return None
        if project.applicant_id != user_id:
            raise ValueError("Only the applicant can edit this project")
        if project.status not in ["draft", "rejected"]:
            raise ValueError(f"Project cannot be edited in status: {project.status}")

        if title:
            project.title = title
        
        if content:
            # We update the current draft version (the one with the highest version number)
            # Actually, usually if it was rejected, we increment version on re-submission.
            # If it's draft, we just update the existing version record.
            latest_version = db.query(ProjectVersion).filter(ProjectVersion.project_id == project.id).order_by(ProjectVersion.version_number.desc()).first()
            latest_version.content = content
            latest_version.diff_summary = ProjectService._generate_diff_summary(latest_version.content, content)
            
        db.commit()
        db.refresh(project)
        return project

    @staticmethod
    def submit_project(db: Session, project_id: uuid.UUID, user_id: uuid.UUID) -> Project:
        project = db.get(Project, project_id)
        if not project:
            return None
        if project.applicant_id != user_id:
            raise ValueError("Only the applicant can submit this project")
        if project.status not in ["draft", "rejected"]:
            raise ValueError(f"Project is not in a submittable state: {project.status}")

        # If it was rejected, we create a new version on submission? 
        # The prompt says "Applicant can resubmit after rejection" and "Version numbers increment on each submission".
        if project.status == "rejected":
            project.current_version += 1
            latest_version = db.query(ProjectVersion).filter(ProjectVersion.project_id == project.id).order_by(ProjectVersion.version_number.desc()).first()
            
            new_version = ProjectVersion(
                project_id=project.id,
                version_number=project.current_version,
                content=latest_version.content,
                diff_summary=latest_version.diff_summary,
                submitted_at=datetime.now(UTC),
                review_status="pending"
            )
            db.add(new_version)
        else:
            # First submission
            latest_version = db.query(ProjectVersion).filter(ProjectVersion.project_id == project.id).order_by(ProjectVersion.version_number.desc()).first()
            latest_version.submitted_at = datetime.now(UTC)

        project.status = "submitted"
        db.commit()
        db.refresh(project)
        return project

    @staticmethod
    def review_project(db: Session, project_id: uuid.UUID, reviewer_id: uuid.UUID, decision: str, comment: str | None) -> Project:
        project = db.get(Project, project_id)
        if not project:
            return None
        if project.status != "submitted":
             raise ValueError(f"Project is not in submitted state: {project.status}")

        latest_version = db.query(ProjectVersion).filter(ProjectVersion.project_id == project.id).order_by(ProjectVersion.version_number.desc()).first()
        latest_version.reviewer_id = reviewer_id
        latest_version.review_comment = comment
        
        if decision == "approved":
            project.status = "approved"
            latest_version.review_status = "approved"
        elif decision == "rejected":
            project.status = "rejected"
            latest_version.review_status = "rejected"
        else:
            raise ValueError("Invalid review decision. Use 'approved' or 'rejected'")

        db.commit()
        db.refresh(project)
        return project

    @staticmethod
    def deactivate_project(db: Session, project_id: uuid.UUID, user_id: uuid.UUID, is_admin: bool) -> Project:
        project = db.get(Project, project_id)
        if not project:
            return None
        
        # Admin or Applicant (owner) can deactivate
        if not is_admin and project.applicant_id != user_id:
            raise ValueError("Not authorized to deactivate this project")

        if project.status == "deactivated":
             raise ValueError("Project is already deactivated")

        project.status = "deactivated"
        db.commit()
        db.refresh(project)
        return project

    @staticmethod
    def list_projects(db: Session, applicant_id: uuid.UUID | None, status: str | None, page: int, page_size: int) -> tuple[list[Project], int]:
        query = db.query(Project)
        if applicant_id:
            query = query.filter(Project.applicant_id == applicant_id)
        if status:
            query = query.filter(Project.status == status)
            
        total = query.count()
        items = query.order_by(Project.updated_at.desc()).offset((page-1)*page_size).limit(page_size).all()
        return items, total

    @staticmethod
    def get_project_details(db: Session, project_id: uuid.UUID) -> Project | None:
        return db.get(Project, project_id)

    @staticmethod
    def _generate_diff_summary(old_content: dict, new_content: dict) -> str:
        # A very simple diff summary implementation
        if old_content == new_content:
            return "No changes."
        return f"Content updated at {datetime.now(UTC).isoformat()}"
