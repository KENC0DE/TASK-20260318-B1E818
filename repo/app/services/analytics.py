"""Operation Analytics domain service."""

from __future__ import annotations

from datetime import date, datetime, time, UTC
from decimal import Decimal
from typing import Any

from sqlalchemy.orm import Session
from sqlalchemy import func, select, and_

from app.models.order import Order
from app.models.after_sales import AfterSalesOrder
from app.schemas.analytics import DailyMetrics


class AnalyticsService:
    @staticmethod
    def get_daily_metrics(db: Session, target_date: date) -> DailyMetrics:
        start_of_day = datetime.combine(target_date, time.min, tzinfo=UTC)
        end_of_day = datetime.combine(target_date, time.max, tzinfo=UTC)

        # 1. Transaction volume: sum of settled orders
        volume = db.query(func.sum(Order.total)).filter(
            and_(
                Order.status == "settled",
                Order.settled_at >= start_of_day,
                Order.settled_at <= end_of_day
            )
        ).scalar() or Decimal("0.00")

        # 2. Conversion rate: settled / (settled + voided)
        settled_count = db.query(func.count(Order.id)).filter(
            and_(
                Order.status == "settled",
                Order.settled_at >= start_of_day,
                Order.settled_at <= end_of_day
            )
        ).scalar() or 0

        voided_count = db.query(func.count(Order.id)).filter(
            and_(
                Order.status == "voided",
                Order.voided_at >= start_of_day,
                Order.voided_at <= end_of_day
            )
        ).scalar() or 0

        total_settled_voided = settled_count + voided_count
        conversion_rate = (settled_count / total_settled_voided) if total_settled_voided > 0 else 0.0

        # 3. Activity: count unique users with orders (any status)
        unique_users = db.query(func.count(func.distinct(Order.cashier_id))).filter(
            and_(
                Order.created_at >= start_of_day,
                Order.created_at <= end_of_day
            )
        ).scalar() or 0

        # 4. Dispute rate: count after-sales / count settled orders
        after_sales_count = db.query(func.count(AfterSalesOrder.id)).filter(
            and_(
                AfterSalesOrder.created_at >= start_of_day,
                AfterSalesOrder.created_at <= end_of_day
            )
        ).scalar() or 0

        dispute_rate = (after_sales_count / settled_count) if settled_count > 0 else 0.0

        return DailyMetrics(
            date=target_date,
            transaction_volume=volume,
            conversion_rate=float(conversion_rate),
            unique_active_users=unique_users,
            dispute_rate=float(dispute_rate)
        )

    @staticmethod
    def export_daily_metrics(db: Session, target_date: date) -> str:
        metrics = AnalyticsService.get_daily_metrics(db, target_date)
        # Simplified CSV export
        header = "date,transaction_volume,conversion_rate,unique_active_users,dispute_rate"
        row = f"{metrics.date},{metrics.transaction_volume},{metrics.conversion_rate},{metrics.unique_active_users},{metrics.dispute_rate}"
        return f"{header}\n{row}"
