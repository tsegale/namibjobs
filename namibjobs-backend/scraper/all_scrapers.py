"""
NamibJobs — multi-source scraper
Sources: namijob.com, jobs4na.com, najobs.info, jobsnamibia.net,
         jobvacanciesinnamibia.com  (+ existing myjob.com.na)

Each scraper function is isolated — one failing does not stop the others.
Selectors are documented with comments; update them if a site changes layout.
"""

import sys
import time
import logging
from datetime import datetime
from pathlib import Path

import requests
from bs4 import BeautifulSoup
from sqlalchemy.exc import IntegrityError

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from database.database import SessionLocal
from database.models import Job
from scraper.myjob_scraper import scrape as _myjob_scrape

# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger(__name__)

DELAY = 2   # seconds between requests / between scrapers

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _get(url: str, session: requests.Session) -> BeautifulSoup | None:
    try:
        r = session.get(url, headers=HEADERS, timeout=15)
        r.raise_for_status()
        return BeautifulSoup(r.text, "html.parser")
    except requests.RequestException as e:
        log.error("Fetch failed [%s]: %s", url, e)
        return None


def _text(tag) -> str:
    return tag.get_text(" ", strip=True) if tag else ""


def _href(tag, base: str) -> str | None:
    if tag and tag.name != "a":
        tag = tag.find("a")
    if not tag or not tag.has_attr("href"):
        return None
    href = tag["href"].strip()
    if not href or href == "#":
        return None
    return href if href.startswith("http") else base.rstrip("/") + "/" + href.lstrip("/")


def _save(db, *, title: str, company: str, location: str | None = None,
          description: str | None = None, source_url: str, source_name: str) -> bool:
    record = Job(
        title=title,
        company=company or "Unknown",
        location=location,
        description=description,
        source_url=source_url,
        source_name=source_name,
        date_scraped=datetime.utcnow(),
    )
    db.add(record)
    try:
        db.commit()
        return True
    except IntegrityError:
        db.rollback()
        return False


# ---------------------------------------------------------------------------
# 1. myjob.com.na  (existing scraper, wrapped for unified interface)
# ---------------------------------------------------------------------------

def scrape_myjob() -> int:
    """Delegate to the existing myjob_scraper.scrape() implementation."""
    try:
        result = _myjob_scrape()
        return result or 0
    except Exception as e:
        log.error("[myjob.com.na] Scrape failed: %s", e)
        return 0


# ---------------------------------------------------------------------------
# 2. namijob.com
#    Selectors target a WordPress / WP Job Manager layout.
#    Primary card: li.job_listing   Fallback: article, .listing
#    Title:        h3 a             Fallback: h2 a, .job-title a
#    Company:      .company strong  Fallback: .company, .employer
#    Description:  .job_description p
# ---------------------------------------------------------------------------

def scrape_namijob() -> int:
    SOURCE = "namijob.com"
    BASE   = "https://www.namijob.com"
    PAGES  = [
        f"{BASE}/jobs/",
        f"{BASE}/vacancies/",
        f"{BASE}/",
    ]

    http = requests.Session()
    db   = SessionLocal()
    saved = 0

    try:
        log.info("[%s] Starting scrape", SOURCE)
        soup = None
        for url in PAGES:
            soup = _get(url, http)
            if soup:
                break
            time.sleep(DELAY)

        if not soup:
            log.warning("[%s] Could not reach site", SOURCE)
            return 0

        # Try multiple card selectors in priority order
        cards = (
            soup.select("li.job_listing") or
            soup.select("article.type-job_listing") or
            soup.select(".job_listing") or
            soup.select("article.job") or
            soup.select(".listing-item")
        )

        log.info("[%s] Found %d listings", SOURCE, len(cards))

        for card in cards:
            try:
                # Title + URL
                title_tag = (
                    card.select_one("h3 a") or
                    card.select_one("h2 a") or
                    card.select_one(".job-title a") or
                    card.select_one("a")
                )
                title = _text(title_tag)
                url   = _href(title_tag, BASE)
                if not title or not url:
                    continue

                # Company
                company = _text(
                    card.select_one(".company strong") or
                    card.select_one(".company a") or
                    card.select_one(".company") or
                    card.select_one(".employer") or
                    card.select_one(".meta-company")
                ) or "Unknown"

                # Description (brief — from card preview)
                desc = _text(
                    card.select_one(".job_description") or
                    card.select_one(".description") or
                    card.select_one("p")
                ) or None

                if _save(db, title=title, company=company, description=desc,
                         source_url=url, source_name=SOURCE):
                    saved += 1
                    log.info("[%s] Saved: %s @ %s", SOURCE, title, company)

                time.sleep(DELAY)

            except Exception as e:
                log.warning("[%s] Card parse error: %s", SOURCE, e)

    except Exception as e:
        log.error("[%s] Scrape failed: %s", SOURCE, e)
    finally:
        db.close()
        http.close()

    log.info("[%s] Done — %d jobs saved", SOURCE, saved)
    return saved


# ---------------------------------------------------------------------------
# 3. jobs4na.com
#    Layout: HTML job board, possibly table-based or card-based.
#    Card:     .job, article, tr (table row), .vacancy-item
#    Title:    .job-title a, h2 a, h3 a, td:nth-child(1) a
#    Company:  .company, .employer, td:nth-child(2)
#    Location: .location, .area, td:nth-child(3)
# ---------------------------------------------------------------------------

def scrape_jobs4na() -> int:
    SOURCE = "jobs4na.com"
    BASE   = "https://jobs4na.com"
    PAGES  = [
        f"{BASE}/jobs/",
        f"{BASE}/vacancies/",
        f"{BASE}/",
    ]

    http = requests.Session()
    db   = SessionLocal()
    saved = 0

    try:
        log.info("[%s] Starting scrape", SOURCE)
        soup = None
        for url in PAGES:
            soup = _get(url, http)
            if soup:
                break
            time.sleep(DELAY)

        if not soup:
            log.warning("[%s] Could not reach site", SOURCE)
            return 0

        cards = (
            soup.select(".job-item") or
            soup.select("article.job") or
            soup.select(".vacancy-item") or
            soup.select("table.jobs tr") or
            soup.select("ul.jobs li") or
            soup.select(".listing")
        )

        log.info("[%s] Found %d listings", SOURCE, len(cards))

        for card in cards:
            try:
                title_tag = (
                    card.select_one(".job-title a") or
                    card.select_one("h2 a") or
                    card.select_one("h3 a") or
                    card.select_one("td a") or
                    card.select_one("a")
                )
                title = _text(title_tag)
                url   = _href(title_tag, BASE)
                if not title or not url:
                    continue

                company = _text(
                    card.select_one(".company") or
                    card.select_one(".employer") or
                    card.select_one(".company-name")
                ) or "Unknown"

                location = _text(
                    card.select_one(".location") or
                    card.select_one(".area") or
                    card.select_one(".job-location")
                ) or None

                if _save(db, title=title, company=company, location=location,
                         source_url=url, source_name=SOURCE):
                    saved += 1
                    log.info("[%s] Saved: %s @ %s", SOURCE, title, company)

                time.sleep(DELAY)

            except Exception as e:
                log.warning("[%s] Card parse error: %s", SOURCE, e)

    except Exception as e:
        log.error("[%s] Scrape failed: %s", SOURCE, e)
    finally:
        db.close()
        http.close()

    log.info("[%s] Done — %d jobs saved", SOURCE, saved)
    return saved


# ---------------------------------------------------------------------------
# 4. najobs.info
#    Layout: blog/listing style site.
#    Card:         article.post, .job-listing, li
#    Title:        h2 a, h1 a, .entry-title a
#    Company:      .job-company, .company, .meta-company, .employer
#    Closing date: .closing-date, .deadline, time, .date
#    URL stored as source_url; closing date stored in description field.
# ---------------------------------------------------------------------------

def scrape_najobs() -> int:
    SOURCE = "najobs.info"
    BASE   = "https://najobs.info"
    PAGES  = [
        f"{BASE}/",
        f"{BASE}/jobs/",
        f"{BASE}/vacancies/",
    ]

    http = requests.Session()
    db   = SessionLocal()
    saved = 0

    try:
        log.info("[%s] Starting scrape", SOURCE)
        soup = None
        for url in PAGES:
            soup = _get(url, http)
            if soup:
                break
            time.sleep(DELAY)

        if not soup:
            log.warning("[%s] Could not reach site", SOURCE)
            return 0

        cards = (
            soup.select("article.post") or
            soup.select(".job-listing") or
            soup.select("article") or
            soup.select("li.job") or
            soup.select(".entry")
        )

        log.info("[%s] Found %d listings", SOURCE, len(cards))

        for card in cards:
            try:
                title_tag = (
                    card.select_one("h2 a") or
                    card.select_one("h1 a") or
                    card.select_one(".entry-title a") or
                    card.select_one("a")
                )
                title = _text(title_tag)
                url   = _href(title_tag, BASE)
                if not title or not url:
                    continue

                company = _text(
                    card.select_one(".job-company") or
                    card.select_one(".company") or
                    card.select_one(".meta-company") or
                    card.select_one(".employer")
                ) or "Unknown"

                # Closing date → stored in description
                closing_tag = (
                    card.select_one(".closing-date") or
                    card.select_one(".deadline") or
                    card.select_one("time") or
                    card.select_one(".date")
                )
                desc = (f"Closing: {_text(closing_tag)}") if closing_tag else None

                if _save(db, title=title, company=company, description=desc,
                         source_url=url, source_name=SOURCE):
                    saved += 1
                    log.info("[%s] Saved: %s @ %s", SOURCE, title, company)

                time.sleep(DELAY)

            except Exception as e:
                log.warning("[%s] Card parse error: %s", SOURCE, e)

    except Exception as e:
        log.error("[%s] Scrape failed: %s", SOURCE, e)
    finally:
        db.close()
        http.close()

    log.info("[%s] Done — %d jobs saved", SOURCE, saved)
    return saved


# ---------------------------------------------------------------------------
# 5. jobsnamibia.net
#    Layout: WordPress blog-style listing.
#    Card:        article.post, .job-item, .listing-item
#    Title:       h2.entry-title a, h2 a, h3 a
#    Location:    .job-location, .location, .meta-location
#    Description: .entry-excerpt, .job-description, .entry-content p:first-child
# ---------------------------------------------------------------------------

def scrape_jobsnamibia() -> int:
    SOURCE = "jobsnamibia.net"
    BASE   = "https://www.jobsnamibia.net"
    PAGES  = [
        f"{BASE}/",
        f"{BASE}/jobs/",
        f"{BASE}/vacancies/",
    ]

    http = requests.Session()
    db   = SessionLocal()
    saved = 0

    try:
        log.info("[%s] Starting scrape", SOURCE)
        soup = None
        for url in PAGES:
            soup = _get(url, http)
            if soup:
                break
            time.sleep(DELAY)

        if not soup:
            log.warning("[%s] Could not reach site", SOURCE)
            return 0

        cards = (
            soup.select("article.post") or
            soup.select(".job-item") or
            soup.select("article") or
            soup.select(".listing-item") or
            soup.select(".entry")
        )

        log.info("[%s] Found %d listings", SOURCE, len(cards))

        for card in cards:
            try:
                title_tag = (
                    card.select_one("h2.entry-title a") or
                    card.select_one("h2 a") or
                    card.select_one("h3 a") or
                    card.select_one(".job-title a") or
                    card.select_one("a")
                )
                title = _text(title_tag)
                url   = _href(title_tag, BASE)
                if not title or not url:
                    continue

                location = _text(
                    card.select_one(".job-location") or
                    card.select_one(".location") or
                    card.select_one(".meta-location")
                ) or None

                desc = _text(
                    card.select_one(".entry-excerpt") or
                    card.select_one(".job-description") or
                    card.select_one(".entry-content p")
                ) or None

                # jobsnamibia.net doesn't always expose company on listing page
                company = _text(
                    card.select_one(".company") or
                    card.select_one(".employer") or
                    card.select_one(".meta-company")
                ) or "Unknown"

                if _save(db, title=title, company=company, location=location,
                         description=desc, source_url=url, source_name=SOURCE):
                    saved += 1
                    log.info("[%s] Saved: %s", SOURCE, title)

                time.sleep(DELAY)

            except Exception as e:
                log.warning("[%s] Card parse error: %s", SOURCE, e)

    except Exception as e:
        log.error("[%s] Scrape failed: %s", SOURCE, e)
    finally:
        db.close()
        http.close()

    log.info("[%s] Done — %d jobs saved", SOURCE, saved)
    return saved


# ---------------------------------------------------------------------------
# 6. jobvacanciesinnamibia.com
#    Layout: blog / Blogger / WordPress style.
#    Card:    article.post, .post, .entry, .hentry
#    Title:   h1.entry-title a, h2 a, .post-title a
#    Company: .company, p strong:first-child, .meta-company
# ---------------------------------------------------------------------------

def scrape_jobvacancies() -> int:
    SOURCE = "jobvacanciesinnamibia.com"
    BASE   = "https://jobvacanciesinnamibia.com"
    PAGES  = [
        f"{BASE}/",
        f"{BASE}/p/jobs.html",
        f"{BASE}/search/label/Jobs",
    ]

    http = requests.Session()
    db   = SessionLocal()
    saved = 0

    try:
        log.info("[%s] Starting scrape", SOURCE)
        soup = None
        for url in PAGES:
            soup = _get(url, http)
            if soup:
                break
            time.sleep(DELAY)

        if not soup:
            log.warning("[%s] Could not reach site", SOURCE)
            return 0

        cards = (
            soup.select("article.post") or
            soup.select(".post.hentry") or
            soup.select("article") or
            soup.select(".entry") or
            soup.select(".hentry")
        )

        log.info("[%s] Found %d listings", SOURCE, len(cards))

        for card in cards:
            try:
                title_tag = (
                    card.select_one("h1.entry-title a") or
                    card.select_one("h2.post-title a") or
                    card.select_one("h2 a") or
                    card.select_one("h3 a") or
                    card.select_one(".post-title a") or
                    card.select_one("a")
                )
                title = _text(title_tag)
                url   = _href(title_tag, BASE)
                if not title or not url:
                    continue

                company = _text(
                    card.select_one(".company") or
                    card.select_one(".meta-company") or
                    card.select_one(".employer")
                ) or "Unknown"

                if _save(db, title=title, company=company,
                         source_url=url, source_name=SOURCE):
                    saved += 1
                    log.info("[%s] Saved: %s @ %s", SOURCE, title, company)

                time.sleep(DELAY)

            except Exception as e:
                log.warning("[%s] Card parse error: %s", SOURCE, e)

    except Exception as e:
        log.error("[%s] Scrape failed: %s", SOURCE, e)
    finally:
        db.close()
        http.close()

    log.info("[%s] Done — %d jobs saved", SOURCE, saved)
    return saved


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------

SCRAPER_REGISTRY = [
    ("myjob.com.na",              scrape_myjob),
    ("namijob.com",               scrape_namijob),
    ("jobs4na.com",               scrape_jobs4na),
    ("najobs.info",               scrape_najobs),
    ("jobsnamibia.net",           scrape_jobsnamibia),
    ("jobvacanciesinnamibia.com", scrape_jobvacancies),
]


def run_all_scrapers() -> dict:
    """Run every scraper in sequence and print a summary table."""
    log.info("=" * 60)
    log.info("NamibJobs — full scrape run started at %s", datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"))
    log.info("=" * 60)

    results = {}
    for name, fn in SCRAPER_REGISTRY:
        log.info(">>> Scraping %s", name)
        results[name] = fn()
        time.sleep(DELAY)

    # ── Summary table ──────────────────────────────────────────────
    col = 34
    total = sum(results.values())
    bar = "=" * (col + 18)
    print(f"\n{bar}")
    print(f"  {'NAMIBJOBS SCRAPE SUMMARY':^{col + 14}}")
    print(bar)
    for source, count in results.items():
        status = "OK" if count > 0 else "0 / unreachable"
        print(f"  {source:<{col}} {count:>4}   [{status}]")
    print("-" * (col + 18))
    print(f"  {'TOTAL':<{col}} {total:>4}")
    print(f"{bar}\n")

    return results


if __name__ == "__main__":
    run_all_scrapers()
