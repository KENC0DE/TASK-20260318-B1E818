"""Attachment API routes."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.core.auth import require_role
from app.db.session import get_db
from app.models.auth import User, UserRole
from app.schemas.attachment import AttachmentResponse
from app.services.attachment import AttachmentService

router = APIRouter(prefix="/attachments", tags=["Attachments"])


@router.post("", response_model=AttachmentResponse, status_code=status.HTTP_201_CREATED)
async def upload_attachment(
    owner_type: Annotated[str, Form(...)],
    owner_id: Annotated[uuid.UUID, Form(...)],
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.APPLICANT, UserRole.CASHIER, UserRole.STORE_MANAGER, UserRole.ADMIN, UserRole.REVIEWER)),
) -> AttachmentResponse:
    try:
        attachment = AttachmentService.save_upload(
            db=db,
            file=file.file,
            filename=file.filename,
            mime_type=file.content_type,
            owner_type=owner_type,
            owner_id=owner_id,
            user_id=current_user.id
        )
        return AttachmentResponse.model_validate(attachment)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.get("/{attachment_id}", response_model=AttachmentResponse)
def get_attachment_metadata(
    attachment_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.APPLICANT, UserRole.CASHIER, UserRole.STORE_MANAGER, UserRole.ADMIN, UserRole.REVIEWER)),
) -> AttachmentResponse:
    try:
        attachment = AttachmentService.get_attachment(db, attachment_id, current_user.id, current_user.role.value)
        if not attachment:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Attachment not found")
        return AttachmentResponse.model_validate(attachment)
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))


@router.get("/{attachment_id}/download")
def download_attachment(
    attachment_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.APPLICANT, UserRole.CASHIER, UserRole.STORE_MANAGER, UserRole.ADMIN, UserRole.REVIEWER)),
) -> FileResponse:
    try:
        attachment = AttachmentService.get_attachment(db, attachment_id, current_user.id, current_user.role.value)
        if not attachment:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Attachment not found")
        
        return FileResponse(
            path=attachment.file_path,
            filename=attachment.filename,
            media_type=attachment.mime_type
        )
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))
