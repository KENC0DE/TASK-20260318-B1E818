"""Operation Analytics pydantic schemas."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from pydantic import BaseModel


class DailyMetrics(BaseModel):
    date: date
    transaction_volume: Decimal
    conversion_rate: float
    unique_active_users: int
    dispute_rate: float
