"""Operation Analytics API routes."""

from __future__ import annotations

from datetime import date
from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.orm import Session

from app.core.auth import require_role
from app.db.session import get_db
from app.models.auth import User, UserRole
from app.schemas.analytics import DailyMetrics
from app.services.analytics import AnalyticsService

router = APIRouter(prefix="/analytics", tags=["Analytics"])


@router.get("/daily", response_model=DailyMetrics)
def get_daily_metrics(
    target_date: date = Query(default_factory=date.today),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN, UserRole.STORE_MANAGER)),
) -> DailyMetrics:
    """
    Get daily operation metrics (Admin/Store Manager only).
    """
    return AnalyticsService.get_daily_metrics(db, target_date)


@router.get("/export")
def export_metrics(
    target_date: date = Query(default_factory=date.today),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN, UserRole.STORE_MANAGER)),
) -> Response:
    """
    Export daily operation metrics as CSV (Admin/Store Manager only).
    """
    csv_data = AnalyticsService.export_daily_metrics(db, target_date)
    return Response(
        content=csv_data,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=metrics_{target_date}.csv"}
    )
