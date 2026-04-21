"""Background task scheduler."""

from apscheduler.schedulers.background import BackgroundScheduler
from app.db.session import SessionLocal
from app.services.order import OrderService
from app.services.feature import FeatureService
import logging

logger = logging.getLogger(__name__)

scheduler = BackgroundScheduler()

def auto_void_job():
    """Wrapper to run auto-void with a fresh DB session."""
    db = SessionLocal()
    try:
        count = OrderService.auto_void_pending_orders(db)
        if count > 0:
            logger.info(f"Auto-voided {count} pending orders.")
    except Exception as e:
        logger.error(f"Error in auto_void_job: {e}")
    finally:
        db.close()

def feature_ttl_job():
    """Wrapper to run feature TTL management with a fresh DB session."""
    db = SessionLocal()
    try:
        count = FeatureService.move_expired_hot_to_cold(db)
        if count > 0:
            logger.info(f"Moved {count} expired hot feature values to cold storage.")
    except Exception as e:
        logger.error(f"Error in feature_ttl_job: {e}")
    finally:
        db.close()

def start_scheduler():
    if not scheduler.running:
        scheduler.add_job(auto_void_job, 'interval', minutes=1, id='auto_void_orders')
        scheduler.add_job(feature_ttl_job, 'interval', minutes=5, id='feature_ttl_management')
        scheduler.start()
        logger.info("Background scheduler started.")

def stop_scheduler():
    if scheduler.running:
        scheduler.shutdown()
        logger.info("Background scheduler stopped.")
