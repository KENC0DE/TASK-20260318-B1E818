"""Project and ProjectVersion ORM models."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Integer, String, Uuid, func, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base

if TYPE_CHECKING:
    from app.models.auth import User


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    applicant_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("users.id"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(256), nullable=False)
    
    # draft / submitted / under_review / approved / rejected / deactivated
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="draft")
    current_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    applicant: Mapped[User] = relationship("User", foreign_keys=[applicant_id])
    versions: Mapped[list[ProjectVersion]] = relationship(
        "ProjectVersion", back_populates="project", cascade="all, delete-orphan", order_by="ProjectVersion.version_number.desc()"
    )


class ProjectVersion(Base):
    __tablename__ = "project_versions"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("projects.id"), nullable=False, index=True)
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    
    content: Mapped[dict] = mapped_column(JSON, nullable=False)
    diff_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    
    reviewer_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("users.id"), nullable=True)
    review_comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    # pending / approved / rejected
    review_status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")

    project: Mapped[Project] = relationship("Project", back_populates="versions")
    reviewer: Mapped[User | None] = relationship("User", foreign_keys=[reviewer_id])
