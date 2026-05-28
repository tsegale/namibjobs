"""
NamibJobs scraper scheduler — runs all scrapers every 24 hours.
Usage: python scheduler.py
"""
import sys
import logging
from pathlib import Path

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.interval import IntervalTrigger

sys.path.insert(0, str(Path(__file__).resolve().parent))
from scraper.all_scrapers import run_all_scrapers

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger(__name__)


def main():
    log.info("NamibJobs scheduler starting — running immediately, then every 24 hours.")
    run_all_scrapers()

    scheduler = BlockingScheduler()
    scheduler.add_job(
        run_all_scrapers,
        trigger=IntervalTrigger(hours=24),
        id="namibjobs_full_scrape",
        replace_existing=True,
    )
    log.info("Scheduler running. Press Ctrl+C to stop.")
    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        log.info("Scheduler stopped.")


if __name__ == "__main__":
    main()
