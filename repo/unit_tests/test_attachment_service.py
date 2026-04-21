"""Unit tests for AttachmentService."""

from __future__ import annotations

import io
import uuid
import pytest
from sqlalchemy.orm import Session

from app.models.auth import User, UserRole
from app.services.attachment import AttachmentService


@pytest.fixture
def uploader(db_session: Session) -> User:
    user = User(
        username=f"uploader_{uuid.uuid4().hex[:6]}",
        password_hash="hash",
        role=UserRole.APPLICANT,
    )
    db_session.add(user)
    db_session.commit()
    return user


def test_upload_attachment_success(db_session: Session, uploader: User) -> None:
    file_content = b"test pdf content"
    file = io.BytesIO(file_content)
    owner_id = uuid.uuid4()
    
    attachment = AttachmentService.save_upload(
        db=db_session,
        file=file,
        filename="test.pdf",
        mime_type="application/pdf",
        owner_type="project_version",
        owner_id=owner_id,
        user_id=uploader.id
    )
    
    assert attachment.id is not None
    assert attachment.filename == "test.pdf"
    assert attachment.file_size == len(file_content)


def test_upload_duplicate_returns_existing(db_session: Session, uploader: User) -> None:
    file_content = b"same content"
    owner_id = uuid.uuid4()
    
    att1 = AttachmentService.save_upload(
        db=db_session,
        file=io.BytesIO(file_content),
        filename="first.png",
        mime_type="image/png",
        owner_type="test",
        owner_id=owner_id,
        user_id=uploader.id
    )
    
    att2 = AttachmentService.save_upload(
        db=db_session,
        file=io.BytesIO(file_content),
        filename="second.png",
        mime_type="image/png",
        owner_type="test",
        owner_id=owner_id,
        user_id=uploader.id
    )
    
    assert att1.id == att2.id


def test_upload_invalid_mime_fails(db_session: Session, uploader: User) -> None:
    file = io.BytesIO(b"evil exe content")
    with pytest.raises(ValueError, match="Disallowed file format"):
        AttachmentService.save_upload(
            db=db_session,
            file=file,
            filename="evil.exe",
            mime_type="application/x-msdownload",
            owner_type="test",
            owner_id=uuid.uuid4(),
            user_id=uploader.id
        )


def test_upload_oversized_fails(db_session: Session, uploader: User) -> None:
    # Mocking a large file by just passing a large BytesIO would work, 
    # but we actually read it. 21MB is not too large for memory in tests.
    file = io.BytesIO(b"0" * (21 * 1024 * 1024))
    with pytest.raises(ValueError, match="exceeds 20MB limit"):
        AttachmentService.save_upload(
            db=db_session,
            file=file,
            filename="large.pdf",
            mime_type="application/pdf",
            owner_type="test",
            owner_id=uuid.uuid4(),
            user_id=uploader.id
        )
