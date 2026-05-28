import sys
import time
import random
import logging
from datetime import datetime
from pathlib import Path

import requests
from bs4 import BeautifulSoup
from sqlalchemy.exc import IntegrityError

sys.path.append(str(Path(__file__).resolve().parent.parent))

from database.database import SessionLocal
from database.models import Job

# ---------------------------------------------------------------------------
# Selectors — update these if the site changes its markup
# ---------------------------------------------------------------------------
BASE_URL = "https://www.myjob.com.na"
LISTING_PATH = "/Jobs/"

CARD_SELECTOR = "div.job-item"             # container for one job card
TITLE_SELECTOR = "h2.job-title a"          # job title + href
COMPANY_SELECTOR = "span.company-name"     # company name
LOCATION_SELECTOR = "span.location"        # location text
NEXT_PAGE_SELECTOR = "a.next-page"         # pagination "next" link

SOURCE_NAME = "myjob.com.na"
REQUEST_DELAY = (2, 5)   # random sleep range in seconds between requests
MAX_PAGES = 20           # safety cap
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}


def get_page(url: str, session: requests.Session) -> BeautifulSoup | None:
    try:
        response = session.get(url, headers=HEADERS, timeout=15)
        response.raise_for_status()
        return BeautifulSoup(response.text, "html.parser")
    except requests.RequestException as e:
        log.error("Failed to fetch %s: %s", url, e)
        return None


def parse_cards(soup: BeautifulSoup) -> list[dict]:
    jobs = []
    cards = soup.select(CARD_SELECTOR)

    if not cards:
        log.warning("No job cards found — selector may need updating: %s", CARD_SELECTOR)

    for card in cards:
        try:
            title_tag = card.select_one(TITLE_SELECTOR)
            title = title_tag.get_text(strip=True) if title_tag else None
            href = title_tag["href"] if title_tag and title_tag.has_attr("href") else None
            source_url = href if href and href.startswith("http") else (BASE_URL + href if href else None)

            company_tag = card.select_one(COMPANY_SELECTOR)
            company = company_tag.get_text(strip=True) if company_tag else "Unknown"

            location_tag = card.select_one(LOCATION_SELECTOR)
            location = location_tag.get_text(strip=True) if location_tag else None

            if not title or not source_url:
                log.debug("Skipping incomplete card: title=%s url=%s", title, source_url)
                continue

            jobs.append({
                "title": title,
                "company": company,
                "location": location,
                "source_url": source_url,
            })
        except Exception as e:
            log.warning("Error parsing card: %s", e)

    return jobs


def fetch_description(url: str, session: requests.Session) -> str | None:
    soup = get_page(url, session)
    if not soup:
        return None
    # Try common description containers in order
    for selector in ("div.job-description", "div#job-description", "section.description", "div.description"):
        tag = soup.select_one(selector)
        if tag:
            return tag.get_text(separator="\n", strip=True)
    # Fallback: largest <p> block on the page
    paragraphs = soup.find_all("p")
    if paragraphs:
        return "\n".join(p.get_text(strip=True) for p in paragraphs if len(p.get_text(strip=True)) > 40)
    return None


def next_page_url(soup: BeautifulSoup) -> str | None:
    tag = soup.select_one(NEXT_PAGE_SELECTOR)
    if not tag or not tag.has_attr("href"):
        return None
    href = tag["href"]
    return href if href.startswith("http") else BASE_URL + href


def save_job(db, job_data: dict) -> bool:
    record = Job(
        title=job_data["title"],
        company=job_data["company"],
        location=job_data.get("location"),
        description=job_data.get("description"),
        source_url=job_data["source_url"],
        source_name=SOURCE_NAME,
        date_scraped=datetime.utcnow(),
    )
    db.add(record)
    try:
        db.commit()
        return True
    except IntegrityError:
        db.rollback()
        log.debug("Duplicate skipped: %s", job_data["source_url"])
        return False


def scrape():
    http = requests.Session()
    db = SessionLocal()
    url = BASE_URL + LISTING_PATH
    page = 1
    total_saved = 0
    total_seen = 0

    try:
        while url and page <= MAX_PAGES:
            log.info("Scraping page %d: %s", page, url)
            soup = get_page(url, http)

            if not soup:
                log.error("Aborting — could not load page %d.", page)
                break

            cards = parse_cards(soup)
            log.info("Found %d listings on page %d.", len(cards), page)

            for card in cards:
                total_seen += 1
                time.sleep(random.uniform(*REQUEST_DELAY))

                card["description"] = fetch_description(card["source_url"], http)
                saved = save_job(db, card)
                if saved:
                    total_saved += 1
                    log.info("[%d saved] %s @ %s", total_saved, card["title"], card["company"])

            url = next_page_url(soup)
            page += 1

            if url:
                time.sleep(random.uniform(*REQUEST_DELAY))

    finally:
        db.close()
        http.close()

    log.info("Done. %d new jobs saved out of %d seen.", total_saved, total_seen)
    return total_saved


if __name__ == "__main__":
    scrape()
