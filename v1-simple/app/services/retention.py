"""Data retention cron job — run weekly."""
import logging
from datetime import datetime, timezone, timedelta
from sqlalchemy import delete, update
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import AsyncSessionLocal
from app.models import Notification

logger = logging.getLogger(__name__)


async def run_retention(db: AsyncSession | None = None) -> dict:
    """
    Retention rules:
    - Delete Notifications older than 365 days
    Returns counts of affected rows.
    """
    own_session = db is None
    if own_session:
        db = AsyncSessionLocal()

    try:
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        results = {}

        # Notifications older than 365 days
        cutoff_365 = now - timedelta(days=365)
        r = await db.execute(
            delete(Notification).where(Notification.created_at < cutoff_365)
        )
        results["notifications_deleted"] = r.rowcount

        await db.commit()
        logger.info("Retention job complete: %s", results)
        return results
    finally:
        if own_session:
            await db.close()


async def cron_retention():
    """Entry point for arq cron."""
    async with AsyncSessionLocal() as db:
        results = await run_retention(db)
        return results
