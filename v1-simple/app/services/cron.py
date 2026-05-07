"""Periodic cron tasks — run via arq worker or direct call."""
import asyncio
import logging
from app.database import AsyncSessionLocal
from app.services.notification_service import run_due_soon_check, run_overdue_check

logger = logging.getLogger(__name__)


async def cron_due_soon():
    async with AsyncSessionLocal() as db:
        count = await run_due_soon_check(db)
        logger.info("cron_due_soon: sent %d notifications", count)


async def cron_overdue():
    async with AsyncSessionLocal() as db:
        count = await run_overdue_check(db)
        logger.info("cron_overdue: sent %d notifications", count)


class WorkerSettings:
    """arq worker settings — run with: arq app.services.cron.WorkerSettings"""
    functions = [cron_due_soon, cron_overdue]
    cron_jobs = [
        # Run both checks every hour
    ]
    # If Redis not available, arq won't start — that's fine for local dev
    redis_settings = None  # reads REDIS_URL from env via arq defaults
