"""Attachment domain service."""

from __future__ import annotations

import hashlib
import os
import uuid
from typing import BinaryIO

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.attachment import Attachment
from app.core.audit import AuditService


class AttachmentService:
    @staticmethod
    def save_upload(
        db: Session,
        file: BinaryIO,
        filename: str,
        mime_type: str,
        owner_type: str,
        owner_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> Attachment:
        # 1. Validation
        allowed_mimes = ["application/pdf", "image/jpeg", "image/png"]
        if mime_type not in allowed_mimes:
            raise ValueError(f"Disallowed file format: {mime_type}. Only PDF, JPG, PNG allowed.")

        # 2. Read and fingerprint
        content = file.read()
        file_size = len(content)
        
        # Max size: 20MB
        if file_size > 20 * 1024 * 1024:
            raise ValueError("File exceeds 20MB limit.")

        fingerprint = hashlib.sha256(content).hexdigest()

        # 3. Handle duplicate uploads (same hash)
        existing = db.query(Attachment).filter(Attachment.sha256_fingerprint == fingerprint).first()
        if existing:
            # We could link the existing file to the new owner, 
            # but for simplicity we'll just return it if owner matches, 
            # or create a new metadata record pointing to same file.
            # Requirement says "Same file re-uploaded -> 200 (return existing)".
            return existing

        # 4. Save to disk
        os.makedirs(settings.upload_dir, exist_ok=True)
        file_ext = os.path.splitext(filename)[1]
        storage_filename = f"{uuid.uuid4()}{file_ext}"
        storage_path = os.path.join(settings.upload_dir, storage_filename)
        
        with open(storage_path, "wb") as f:
            f.write(content)

        # 5. Save metadata
        attachment = Attachment(
            owner_type=owner_type,
            owner_id=owner_id,
            filename=filename,
            file_path=storage_path,
            file_size=file_size,
            mime_type=mime_type,
            sha256_fingerprint=fingerprint,
            uploaded_by=user_id
        )
        db.add(attachment)
        db.commit()
        db.refresh(attachment)
        
        return attachment

    @staticmethod
    def get_attachment(db: Session, attachment_id: uuid.UUID, user_id: uuid.UUID, user_role: str) -> Attachment | None:
        attachment = db.get(Attachment, attachment_id)
        if not attachment:
            return None

        # 1. Admin and Reviewer can access everything
        is_privileged = user_role in ["admin", "reviewer"]
        is_uploader = attachment.uploaded_by == user_id
        
        if is_privileged or is_uploader:
            pass
        # 2. Object-level check (e.g., if it belongs to a project)
        elif attachment.owner_type == "project":
            from app.models.project import Project
            project = db.get(Project, attachment.owner_id)
            if not project or project.applicant_id != user_id:
                raise PermissionError("Not authorized to access this attachment")
        elif attachment.owner_type == "project_version":
            from app.models.project import ProjectVersion
            version = db.get(ProjectVersion, attachment.owner_id)
            if not version or version.project.applicant_id != user_id:
                raise PermissionError("Not authorized to access this attachment")
        else:
            # Not privileged, not uploader, and no special owner rules matched
            raise PermissionError("Not authorized to access this attachment")

        # Log access
        AuditService.write(
            db=db,
            actor_id=user_id,
            action="attachment_access",
            target_type="attachment",
            target_id=attachment.id,
            metadata={"filename": attachment.filename}
        )
        db.commit()
        return attachment
