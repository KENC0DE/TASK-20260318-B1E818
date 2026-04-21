"""Unit tests for ProjectService."""

from __future__ import annotations

import uuid
import pytest
from sqlalchemy.orm import Session

from app.models.auth import User, UserRole
from app.models.project import Project, ProjectVersion
from app.services.project import ProjectService


@pytest.fixture
def applicant(db_session: Session) -> User:
    user = User(
        username=f"applicant_{uuid.uuid4().hex[:6]}",
        password_hash="hash",
        role=UserRole.APPLICANT,
    )
    db_session.add(user)
    db_session.commit()
    return user


@pytest.fixture
def reviewer(db_session: Session) -> User:
    user = User(
        username=f"reviewer_{uuid.uuid4().hex[:6]}",
        password_hash="hash",
        role=UserRole.REVIEWER,
    )
    db_session.add(user)
    db_session.commit()
    return user


def test_create_project_success(db_session: Session, applicant: User) -> None:
    project = ProjectService.create_project(
        db_session, applicant.id, "Test Project", {"key": "value"}
    )
    
    assert project.id is not None
    assert project.status == "draft"
    assert project.current_version == 1
    assert len(project.versions) == 1
    assert project.versions[0].content == {"key": "value"}


def test_update_project_happy_path(db_session: Session, applicant: User) -> None:
    project = ProjectService.create_project(
        db_session, applicant.id, "Old Title", {"key": "old"}
    )
    
    updated = ProjectService.update_project(
        db_session, project.id, applicant.id, "New Title", {"key": "new"}
    )
    
    assert updated.title == "New Title"
    assert updated.versions[0].content == {"key": "new"}


def test_update_project_unauthorized(db_session: Session, applicant: User) -> None:
    project = ProjectService.create_project(
        db_session, applicant.id, "Title", {}
    )
    other_id = uuid.uuid4()
    
    with pytest.raises(ValueError, match="Only the applicant can edit"):
        ProjectService.update_project(db_session, project.id, other_id, "New", {})


def test_submit_project_lifecycle(db_session: Session, applicant: User) -> None:
    project = ProjectService.create_project(db_session, applicant.id, "Submittable", {})
    
    # First submit
    submitted = ProjectService.submit_project(db_session, project.id, applicant.id)
    assert submitted.status == "submitted"
    assert submitted.versions[0].submitted_at is not None


def test_resubmit_after_rejection(db_session: Session, applicant: User, reviewer: User) -> None:
    project = ProjectService.create_project(db_session, applicant.id, "Title", {"v": 1})
    ProjectService.submit_project(db_session, project.id, applicant.id)
    ProjectService.review_project(db_session, project.id, reviewer.id, "rejected", "Fix it")
    
    assert project.status == "rejected"
    
    # Resubmit
    resubmitted = ProjectService.submit_project(db_session, project.id, applicant.id)
    assert resubmitted.status == "submitted"
    assert resubmitted.current_version == 2
    assert len(resubmitted.versions) == 2


def test_review_project_success(db_session: Session, applicant: User, reviewer: User) -> None:
    project = ProjectService.create_project(db_session, applicant.id, "Review me", {})
    ProjectService.submit_project(db_session, project.id, applicant.id)
    
    reviewed = ProjectService.review_project(db_session, project.id, reviewer.id, "approved", "LGTM")
    assert reviewed.status == "approved"
    assert reviewed.versions[0].review_status == "approved"
    assert reviewed.versions[0].reviewer_id == reviewer.id
