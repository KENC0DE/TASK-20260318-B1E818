"""Audit write helpers."""

from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from app.models.audit import AuditLog


class AuditService:
    @staticmethod
    def write(
        db: Session,
        action: str,
        actor_id: uuid.UUID | None = None,
        target_type: str | None = None,
        target_id: uuid.UUID | None = None,
        metadata: dict | None = None,
    ) -> AuditLog:
        entry = AuditLog(
            actor_id=actor_id,
            action=action,
            target_type=target_type,
            target_id=target_id,
            metadata_json=metadata or {},
        )
        db.add(entry)
        return entry
