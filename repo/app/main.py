"""FastAPI application entrypoint for the Offline Retail Checkout & Project Incubation Platform API.

This module wires all API routers and sets up the application lifespan, including
database table creation and background task scheduling.
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI

from app.api.auth import router as auth_router
from app.api.cart import router as cart_router
from app.api.promotion import router as promotion_router
from app.api.product import router as product_router
from app.api.order import router as order_router
from app.api.after_sales import router as after_sales_router
from app.api.project import router as project_router
from app.api.attachment import router as attachment_router
from app.api.notification import router as notification_router
from app.api.feature import router as feature_router
from app.api.analytics import router as analytics_router
from app.api.configuration import router as config_router
from app.api.audit import router as audit_router
from app.api.shift import router as shift_router
from app.workers.scheduler import start_scheduler, stop_scheduler
from app.db.session import engine, Base

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Create tables
    Base.metadata.create_all(bind=engine)
    # Startup: Start background scheduler
    start_scheduler()
    yield
    # Shutdown: Stop background scheduler
    stop_scheduler()

app = FastAPI(
    title="Offline Retail Checkout & Project Incubation Platform API",
    version="0.1.0",
    description="Backend API for offline retail checkout and project incubation workflows.",
    lifespan=lifespan,
)

app.include_router(auth_router)
app.include_router(product_router)
app.include_router(promotion_router)
app.include_router(cart_router)
app.include_router(order_router)
app.include_router(after_sales_router)
app.include_router(project_router)
app.include_router(attachment_router)
app.include_router(notification_router)
app.include_router(feature_router)
app.include_router(analytics_router)
app.include_router(config_router)
app.include_router(audit_router)
app.include_router(shift_router)


@app.get("/health", tags=["Health"])
def health_check() -> dict[str, str]:
    """Basic liveness endpoint used by tests and container health checks."""
    return {"status": "ok"}
