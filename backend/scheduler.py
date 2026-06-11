"""
Unified background worker.
Run: python scheduler.py
"""

import logging, sys, os
sys.path.insert(0, os.path.dirname(__file__))

from apscheduler.schedulers.blocking import BlockingScheduler
from dotenv import load_dotenv

from db import ensure_schema
from realtime_fetcher import run_realtime_fetcher
from rating_engine import persist_daily_ratings

load_dotenv()
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def _calls_etl():
    try:
        from amocrm_calls import main
        main()
    except Exception as e:
        logger.error("calls ETL: %s", e)


def _telegram_etl():
    try:
        from amocrm_telegram import main
        main()
    except Exception as e:
        logger.error("telegram ETL: %s", e)


def _rating_persist():
    try:
        persist_daily_ratings()
    except Exception as e:
        logger.error("rating persist: %s", e)


if __name__ == "__main__":
    logger.info("Ensuring DB schema…")
    ensure_schema()

    scheduler = BlockingScheduler(timezone="Asia/Tashkent")
    scheduler.add_job(run_realtime_fetcher, "interval", minutes=20,  id="rt_fetcher")
    scheduler.add_job(_calls_etl,           "cron",     hour=6,  minute=0,  id="calls_etl")
    scheduler.add_job(_telegram_etl,        "cron",     hour=6,  minute=5,  id="telegram_etl")
    scheduler.add_job(_rating_persist,      "cron",     hour=22, minute=0,  id="rating_persist")

    logger.info("Jobs: rt_fetcher(20min) calls_etl(06:00) telegram_etl(06:05) rating_persist(22:00)")

    # run once immediately on startup
    run_realtime_fetcher()

    scheduler.start()
