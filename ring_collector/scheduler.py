"""Background scheduler for periodic Ring data collection."""

import os
import logging
import threading
from apscheduler.schedulers.background import BackgroundScheduler

from ring_collector.collector import collect_sync

logger = logging.getLogger(__name__)

_scheduler: BackgroundScheduler | None = None
_lock = threading.Lock()


def start_scheduler():
    global _scheduler
    with _lock:
        if _scheduler is not None:
            return

        interval = int(os.getenv("RING_INTERVAL_MINUTES", "15"))
        _scheduler = BackgroundScheduler()
        _scheduler.add_job(
            _collect_with_logging,
            "interval",
            minutes=interval,
            id="ring_collect",
            replace_existing=True,
        )
        _scheduler.start()
        logger.info(f"Ring collector scheduled every {interval} minutes")


def _collect_with_logging():
    try:
        results = collect_sync()
        logger.info(f"Collection complete: {results}")
    except Exception as e:
        logger.error(f"Collection failed: {e}")
