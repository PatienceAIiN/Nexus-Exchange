from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
import logging

logger = logging.getLogger(__name__)
scheduler = AsyncIOScheduler()

def setup_scheduler(scrape_func):
    """Setup APScheduler with FBIL scrape job at 2 PM IST (8:30 AM UTC)."""
    scheduler.add_job(
        scrape_func,
        CronTrigger(hour=8, minute=30, timezone="UTC"),
        id="fbil_daily_scrape",
        replace_existing=True,
    )
    scheduler.start()
    logger.info("Scheduler started: FBIL scrape at 08:30 UTC daily")
