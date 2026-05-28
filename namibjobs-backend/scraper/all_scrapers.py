"""
NamibJobs — multi-source scraper
Job boards:   myjob.com.na, namijob.com, jobs4na.com, najobs.info,
              jobsnamibia.net, jobvacanciesinnamibia.com
Company pages: MTC Namibia, NamPower, Bank of Windhoek, Nedbank Namibia,
               FNB Namibia, Bank of Namibia, O&L Group, Namib Mills,
               Namdeb, Namport, Gondwana Collection, Telecom Namibia,
               Paratus Namibia
Government:   PSC Namibia, City of Windhoek, NamRA

Each scraper is isolated — one failing does not stop the others.
Static sites use requests + BeautifulSoup.
JS-rendered sites fall back to Selenium headless Chrome via _get_or_js().
"""

import re
import sys
import time
import logging
import unicodedata
from datetime import datetime
from pathlib import Path

import requests
from bs4 import BeautifulSoup
from sqlalchemy.exc import IntegrityError

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from database.database import SessionLocal
from database.models import Job
from scraper.myjob_scraper import scrape as _myjob_scrape

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger(__name__)

DELAY = 3   # seconds between requests / between scrapers

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


def _slug(text: str) -> str:
    """URL-safe slug used to construct pseudo-URLs when individual job pages don't exist."""
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    text = re.sub(r"[^\w\s-]", "", text.lower())
    return re.sub(r"[\s_-]+", "-", text).strip("-")


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
# Selenium helper — used for JS-rendered career portals
# ---------------------------------------------------------------------------

def _get_selenium(url: str, wait_sec: int = 5) -> BeautifulSoup | None:
    """Fetch a JavaScript-rendered page using Selenium headless Chrome.
    Returns None gracefully if selenium / ChromeDriver is not available.
    Install with: pip install selenium
    ChromeDriver must match the installed Chrome version and be in PATH.
    """
    try:
        from selenium import webdriver          # noqa: PLC0415
        from selenium.webdriver.chrome.options import Options  # noqa: PLC0415
    except ImportError:
        log.warning("selenium not installed — cannot JS-render %s", url)
        return None

    opts = Options()
    opts.add_argument("--headless=new")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--disable-gpu")
    opts.add_argument(f"user-agent={HEADERS['User-Agent']}")

    driver = None
    try:
        driver = webdriver.Chrome(options=opts)
        driver.set_page_load_timeout(30)
        driver.get(url)
        time.sleep(wait_sec)    # allow JS to finish rendering
        return BeautifulSoup(driver.page_source, "html.parser")
    except Exception as e:
        log.error("Selenium fetch failed [%s]: %s", url, e)
        return None
    finally:
        if driver:
            try:
                driver.quit()
            except Exception:
                pass


def _get_or_js(url: str, session: requests.Session, wait_sec: int = 5) -> BeautifulSoup | None:
    """Try a plain HTTP fetch first.
    If the response body is too sparse (likely JS-rendered), retry with Selenium.
    """
    soup = _get(url, session)
    if soup and len(soup.get_text(" ", strip=True)) > 500:
        return soup
    log.info("Sparse/failed static fetch at %s — retrying with Selenium", url)
    return _get_selenium(url, wait_sec=wait_sec)


# ---------------------------------------------------------------------------
# Generic single-company career page scraper
# ---------------------------------------------------------------------------

# Broad selector lists that cover most career page layouts.
# Override per-site if a site is identified to use different markup.
_CARD_SELS = [
    ".vacancy-item", ".vacancy", ".job-vacancy",
    ".career-item", ".career",
    ".job-item", ".job-listing", ".job",
    ".position-item", ".position", ".opening",
    "article.job", "article.vacancy", "article.position", "article.career",
    "li.vacancy", "li.job", "li.career", "li.position",
    "tr.vacancy", "tr.job",
    ".careers-item", ".careers-listing", ".career-opportunity",
    ".listing-item",
]

_TITLE_SELS = [
    "h2 a", "h3 a", "h4 a",
    ".job-title a", ".position-title a", ".vacancy-title a",
    ".title a", "a.job-title",
    "h2", "h3", "h4",
    ".job-title", ".position-title", ".vacancy-title",
    "td.position", "td.title",
]

_LOC_SELS = [
    ".location", ".job-location", ".vacancy-location",
    "span.location", "td.location", ".city", ".region",
]

_DESC_SELS = [
    ".description", ".job-description", ".vacancy-description",
    ".summary", ".excerpt", ".requirements", "p.description",
]

_CLOSING_SELS = [
    ".closing-date", ".deadline", ".expiry", ".expiry-date",
    ".application-deadline", "td.deadline", "span.date",
]


def _scrape_company(
    source_name: str,
    base_url: str,
    paths: list[str],
    *,
    card_sels: list[str] | None = None,
    title_sels: list[str] | None = None,
    loc_sels: list[str] | None = None,
    desc_sels: list[str] | None = None,
    closing_sels: list[str] | None = None,
    use_js: bool = False,
) -> int:
    """
    Generic scraper for single-company career pages.

    Iterates `paths` until a page is found that contains job cards matching
    one of the `card_sels` selectors.  Falls back to Selenium when
    `use_js=True` and the static response looks sparse.
    """
    card_sels    = card_sels    or _CARD_SELS
    title_sels   = title_sels   or _TITLE_SELS
    loc_sels     = loc_sels     or _LOC_SELS
    desc_sels    = desc_sels    or _DESC_SELS
    closing_sels = closing_sels or _CLOSING_SELS

    fetch = (lambda u, s: _get_or_js(u, s)) if use_js else _get
    http = requests.Session()
    db   = SessionLocal()
    saved = 0

    def _pick(card, sels):
        for sel in sels:
            tag = card.select_one(sel)
            if tag:
                return tag
        return None

    try:
        log.info("[%s] Starting scrape", source_name)

        soup = None
        careers_url = base_url
        for path in paths:
            url = base_url.rstrip("/") + path
            s = fetch(url, http)
            if not s:
                time.sleep(DELAY)
                continue
            if any(s.select(sel) for sel in card_sels):
                soup = s
                careers_url = url
                break
            time.sleep(DELAY)

        if soup is None:
            log.warning("[%s] No job cards found on any candidate path", source_name)
            return 0

        cards = []
        for sel in card_sels:
            cards = soup.select(sel)
            if cards:
                break

        log.info("[%s] Found %d listings", source_name, len(cards))

        for card in cards:
            try:
                title_tag = _pick(card, title_sels)
                title = _text(title_tag)
                if not title:
                    continue

                link = _href(title_tag, base_url)
                if not link:
                    any_a = card.find("a", href=True)
                    link = _href(any_a, base_url) if any_a else None
                if not link:
                    link = f"{careers_url}#{_slug(title)}"

                location    = _text(_pick(card, loc_sels)) or None
                desc_tag    = _pick(card, desc_sels)
                closing_tag = _pick(card, closing_sels)

                parts = []
                if desc_tag:
                    parts.append(_text(desc_tag))
                if closing_tag:
                    parts.append(f"Closing: {_text(closing_tag)}")
                description = "\n".join(parts) or None

                if _save(db, title=title, company=source_name, location=location,
                         description=description, source_url=link,
                         source_name=source_name):
                    saved += 1
                    log.info("[%s] Saved: %s", source_name, title)

                time.sleep(DELAY)

            except Exception as e:
                log.warning("[%s] Card parse error: %s", source_name, e)

    except Exception as e:
        log.error("[%s] Scrape failed: %s", source_name, e)
    finally:
        db.close()
        http.close()

    log.info("[%s] Done — %d jobs saved", source_name, saved)
    return saved


# ===========================================================================
# Job-board scrapers (1–6)
# ===========================================================================

# ---------------------------------------------------------------------------
# 1. myjob.com.na  — delegates to the dedicated scraper module
# ---------------------------------------------------------------------------

def scrape_myjob() -> int:
    try:
        return _myjob_scrape() or 0
    except Exception as e:
        log.error("[myjob.com.na] Scrape failed: %s", e)
        return 0


# ---------------------------------------------------------------------------
# 2. namijob.com — WordPress / WP Job Manager layout
#    Card:    li.job_listing, article.type-job_listing
#    Title:   h3 a, h2 a
#    Company: .company strong, .employer
# ---------------------------------------------------------------------------

def scrape_namijob() -> int:
    SOURCE = "namijob.com"
    BASE   = "https://www.namijob.com"

    http = requests.Session()
    db   = SessionLocal()
    saved = 0

    try:
        log.info("[%s] Starting scrape", SOURCE)
        soup = None
        for url in [f"{BASE}/jobs/", f"{BASE}/vacancies/", f"{BASE}/"]:
            soup = _get(url, http)
            if soup:
                break
            time.sleep(DELAY)

        if not soup:
            log.warning("[%s] Could not reach site", SOURCE)
            return 0

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
                title_tag = (
                    card.select_one("h3 a") or card.select_one("h2 a") or
                    card.select_one(".job-title a") or card.select_one("a")
                )
                title = _text(title_tag)
                url   = _href(title_tag, BASE)
                if not title or not url:
                    continue

                company = _text(
                    card.select_one(".company strong") or card.select_one(".company a") or
                    card.select_one(".company") or card.select_one(".employer")
                ) or "Unknown"

                desc = _text(
                    card.select_one(".job_description") or
                    card.select_one(".description") or card.select_one("p")
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
        db.close(); http.close()

    log.info("[%s] Done — %d jobs saved", SOURCE, saved)
    return saved


# ---------------------------------------------------------------------------
# 3. jobs4na.com — HTML job board (card or table layout)
# ---------------------------------------------------------------------------

def scrape_jobs4na() -> int:
    SOURCE = "jobs4na.com"
    BASE   = "https://jobs4na.com"

    http = requests.Session()
    db   = SessionLocal()
    saved = 0

    try:
        log.info("[%s] Starting scrape", SOURCE)
        soup = None
        for url in [f"{BASE}/jobs/", f"{BASE}/vacancies/", f"{BASE}/"]:
            soup = _get(url, http)
            if soup:
                break
            time.sleep(DELAY)

        if not soup:
            log.warning("[%s] Could not reach site", SOURCE)
            return 0

        cards = (
            soup.select(".job-item") or soup.select("article.job") or
            soup.select(".vacancy-item") or soup.select("table.jobs tr") or
            soup.select("ul.jobs li") or soup.select(".listing")
        )
        log.info("[%s] Found %d listings", SOURCE, len(cards))

        for card in cards:
            try:
                title_tag = (
                    card.select_one(".job-title a") or card.select_one("h2 a") or
                    card.select_one("h3 a") or card.select_one("td a") or
                    card.select_one("a")
                )
                title = _text(title_tag)
                url   = _href(title_tag, BASE)
                if not title or not url:
                    continue

                company  = _text(card.select_one(".company") or card.select_one(".employer") or
                                  card.select_one(".company-name")) or "Unknown"
                location = _text(card.select_one(".location") or card.select_one(".area") or
                                  card.select_one(".job-location")) or None

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
        db.close(); http.close()

    log.info("[%s] Done — %d jobs saved", SOURCE, saved)
    return saved


# ---------------------------------------------------------------------------
# 4. najobs.info — blog/listing style; closing date stored in description
# ---------------------------------------------------------------------------

def scrape_najobs() -> int:
    SOURCE = "najobs.info"
    BASE   = "https://najobs.info"

    http = requests.Session()
    db   = SessionLocal()
    saved = 0

    try:
        log.info("[%s] Starting scrape", SOURCE)
        soup = None
        for url in [f"{BASE}/", f"{BASE}/jobs/", f"{BASE}/vacancies/"]:
            soup = _get(url, http)
            if soup:
                break
            time.sleep(DELAY)

        if not soup:
            log.warning("[%s] Could not reach site", SOURCE)
            return 0

        cards = (
            soup.select("article.post") or soup.select(".job-listing") or
            soup.select("article") or soup.select("li.job") or soup.select(".entry")
        )
        log.info("[%s] Found %d listings", SOURCE, len(cards))

        for card in cards:
            try:
                title_tag = (
                    card.select_one("h2 a") or card.select_one("h1 a") or
                    card.select_one(".entry-title a") or card.select_one("a")
                )
                title = _text(title_tag)
                url   = _href(title_tag, BASE)
                if not title or not url:
                    continue

                company = _text(
                    card.select_one(".job-company") or card.select_one(".company") or
                    card.select_one(".employer")
                ) or "Unknown"

                closing_tag = (
                    card.select_one(".closing-date") or card.select_one(".deadline") or
                    card.select_one("time") or card.select_one(".date")
                )
                desc = f"Closing: {_text(closing_tag)}" if closing_tag else None

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
        db.close(); http.close()

    log.info("[%s] Done — %d jobs saved", SOURCE, saved)
    return saved


# ---------------------------------------------------------------------------
# 5. jobsnamibia.net — WordPress blog style
# ---------------------------------------------------------------------------

def scrape_jobsnamibia() -> int:
    SOURCE = "jobsnamibia.net"
    BASE   = "https://www.jobsnamibia.net"

    http = requests.Session()
    db   = SessionLocal()
    saved = 0

    try:
        log.info("[%s] Starting scrape", SOURCE)
        soup = None
        for url in [f"{BASE}/", f"{BASE}/jobs/", f"{BASE}/vacancies/"]:
            soup = _get(url, http)
            if soup:
                break
            time.sleep(DELAY)

        if not soup:
            log.warning("[%s] Could not reach site", SOURCE)
            return 0

        cards = (
            soup.select("article.post") or soup.select(".job-item") or
            soup.select("article") or soup.select(".listing-item") or soup.select(".entry")
        )
        log.info("[%s] Found %d listings", SOURCE, len(cards))

        for card in cards:
            try:
                title_tag = (
                    card.select_one("h2.entry-title a") or card.select_one("h2 a") or
                    card.select_one("h3 a") or card.select_one(".job-title a") or
                    card.select_one("a")
                )
                title = _text(title_tag)
                url   = _href(title_tag, BASE)
                if not title or not url:
                    continue

                company  = _text(card.select_one(".company") or card.select_one(".employer") or
                                  card.select_one(".meta-company")) or "Unknown"
                location = _text(card.select_one(".job-location") or card.select_one(".location") or
                                  card.select_one(".meta-location")) or None
                desc     = _text(card.select_one(".entry-excerpt") or
                                  card.select_one(".job-description") or
                                  card.select_one(".entry-content p")) or None

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
        db.close(); http.close()

    log.info("[%s] Done — %d jobs saved", SOURCE, saved)
    return saved


# ---------------------------------------------------------------------------
# 6. jobvacanciesinnamibia.com — Blogger style
# ---------------------------------------------------------------------------

def scrape_jobvacancies() -> int:
    SOURCE = "jobvacanciesinnamibia.com"
    BASE   = "https://jobvacanciesinnamibia.com"

    http = requests.Session()
    db   = SessionLocal()
    saved = 0

    try:
        log.info("[%s] Starting scrape", SOURCE)
        soup = None
        for url in [f"{BASE}/", f"{BASE}/p/jobs.html", f"{BASE}/search/label/Jobs"]:
            soup = _get(url, http)
            if soup:
                break
            time.sleep(DELAY)

        if not soup:
            log.warning("[%s] Could not reach site", SOURCE)
            return 0

        cards = (
            soup.select("article.post") or soup.select(".post.hentry") or
            soup.select("article") or soup.select(".entry") or soup.select(".hentry")
        )
        log.info("[%s] Found %d listings", SOURCE, len(cards))

        for card in cards:
            try:
                title_tag = (
                    card.select_one("h1.entry-title a") or card.select_one("h2.post-title a") or
                    card.select_one("h2 a") or card.select_one("h3 a") or
                    card.select_one(".post-title a") or card.select_one("a")
                )
                title = _text(title_tag)
                url   = _href(title_tag, BASE)
                if not title or not url:
                    continue

                company = _text(
                    card.select_one(".company") or card.select_one(".meta-company") or
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
        db.close(); http.close()

    log.info("[%s] Done — %d jobs saved", SOURCE, saved)
    return saved


# ===========================================================================
# Company career pages (7–19)
# Each delegates to _scrape_company() with site-specific paths.
# use_js=True for banks and telecoms that commonly use JS-rendered portals.
# ===========================================================================

def scrape_mtc() -> int:
    # Known path: /corporate/careers; fallbacks tried in order
    return _scrape_company(
        "MTC Namibia", "https://www.mtc.com.na",
        ["/corporate/careers", "/careers", "/vacancies", "/jobs"],
    )


def scrape_nampower() -> int:
    return _scrape_company(
        "NamPower", "https://www.nampower.com.na",
        ["/careers", "/vacancies", "/human-resources/vacancies", "/about-us/careers", "/"],
    )


def scrape_bank_windhoek() -> int:
    return _scrape_company(
        "Bank of Windhoek", "https://www.bankwindhoek.com.na",
        ["/careers", "/vacancies", "/about-us/careers", "/corporate/careers", "/about/careers"],
        use_js=True,
    )


def scrape_nedbank() -> int:
    # SA-owned bank — likely uses Workday or SmartRecruiters (JS portal)
    return _scrape_company(
        "Nedbank Namibia", "https://www.nedbank.com.na",
        ["/careers", "/vacancies", "/about/careers", "/about-us/careers", "/"],
        use_js=True,
    )


def scrape_fnb() -> int:
    # SA-owned bank — likely uses a JS career portal
    return _scrape_company(
        "FNB Namibia", "https://www.fnbnamibia.com.na",
        ["/careers", "/vacancies", "/about-fnb/careers", "/personal/careers", "/"],
        use_js=True,
    )


def scrape_bon() -> int:
    return _scrape_company(
        "Bank of Namibia", "https://www.bon.com.na",
        ["/careers", "/vacancies", "/about-bon/careers", "/about-us/vacancies", "/"],
    )


def scrape_ol_group() -> int:
    return _scrape_company(
        "O&L Group", "https://www.ol-group.com",
        ["/careers", "/jobs", "/vacancies", "/work-with-us", "/about-us/careers", "/"],
    )


def scrape_namib_mills() -> int:
    return _scrape_company(
        "Namib Mills", "https://www.namibmills.com.na",
        ["/vacancies", "/careers", "/about-us/vacancies", "/jobs", "/"],
    )


def scrape_namdeb() -> int:
    return _scrape_company(
        "Namdeb", "https://www.namdeb.com",
        ["/careers", "/vacancies", "/people", "/about/careers", "/"],
    )


def scrape_namport() -> int:
    return _scrape_company(
        "Namport", "https://www.namport.com.na",
        ["/vacancies", "/careers", "/about-us/vacancies", "/corporate/careers", "/"],
    )


def scrape_gondwana() -> int:
    return _scrape_company(
        "Gondwana Collection", "https://www.gondwana-collection.com",
        ["/careers", "/jobs", "/vacancies", "/work-with-us", "/join-us", "/"],
    )


def scrape_telecom() -> int:
    return _scrape_company(
        "Telecom Namibia", "https://www.telecom.na",
        ["/careers", "/vacancies", "/about-us/careers", "/jobs", "/"],
        use_js=True,
    )


def scrape_paratus() -> int:
    return _scrape_company(
        "Paratus Namibia", "https://www.paratus.com.na",
        ["/careers", "/vacancies", "/about/careers", "/about-us/vacancies", "/"],
    )


# ===========================================================================
# Government portals (20–22)
# ===========================================================================

# ---------------------------------------------------------------------------
# 20. PSC Namibia — Public Service Commission
#     Publishes vacancy circulars; each circular is treated as a job.
#     Ministry is parsed from surrounding text when no dedicated element exists.
# ---------------------------------------------------------------------------

def scrape_psc() -> int:
    SOURCE   = "PSC Namibia"
    BASE_URL = "https://www.psc.gov.na"
    PATHS    = [
        "/vacancy-circulars", "/vacancies", "/circulars",
        "/job-vacancies", "/public-service-vacancies", "/",
    ]

    http = requests.Session()
    db   = SessionLocal()
    saved = 0

    try:
        log.info("[%s] Starting scrape", SOURCE)

        # Find a page that mentions vacancies / circulars
        soup = None
        page_url = BASE_URL
        for path in PATHS:
            url = BASE_URL + path
            s = _get(url, http)
            if not s:
                time.sleep(DELAY)
                continue
            body = s.get_text(" ", strip=True).lower()
            if any(kw in body for kw in ("vacant", "circular", "position", "vacancy")):
                soup = s
                page_url = url
                break
            time.sleep(DELAY)

        if not soup:
            log.warning("[%s] Could not find vacancy page", SOURCE)
            return 0

        # Try structured card selectors first
        cards = (
            soup.select(".vacancy-circular") or soup.select(".vacancy-item") or
            soup.select("article.vacancy") or soup.select("li.circular") or
            soup.select("tr.vacancy") or soup.select(".field-item")
        )

        if cards:
            log.info("[%s] Found %d card elements", SOURCE, len(cards))
            for card in cards:
                try:
                    title_tag = (
                        card.select_one("h2 a") or card.select_one("h3 a") or
                        card.select_one("h4 a") or card.select_one(".title a") or
                        card.select_one("a")
                    )
                    title = _text(title_tag)
                    if not title:
                        continue
                    link = _href(title_tag, BASE_URL) or f"{page_url}#{_slug(title)}"

                    ministry_tag = (
                        card.select_one(".ministry") or card.select_one(".department") or
                        card.select_one(".employer") or card.select_one(".institution")
                    )
                    company = _text(ministry_tag) or "Government of Namibia"

                    location = _text(
                        card.select_one(".location") or card.select_one(".region")
                    ) or None
                    closing_tag = (
                        card.select_one(".closing-date") or card.select_one(".deadline") or
                        card.select_one("time")
                    )
                    desc = f"Closing: {_text(closing_tag)}" if closing_tag else None

                    if _save(db, title=title, company=company, location=location,
                             description=desc, source_url=link, source_name=SOURCE):
                        saved += 1
                        log.info("[%s] Saved: %s @ %s", SOURCE, title, company)
                    time.sleep(DELAY)
                except Exception as e:
                    log.warning("[%s] Card parse error: %s", SOURCE, e)

        else:
            # Fallback: extract all hyperlinks that look like vacancy postings
            log.info("[%s] No card elements — falling back to link extraction", SOURCE)
            vacancy_keywords = ("vacant", "circular", "position", "vacancy", "post", "recruit")
            links = [
                a for a in soup.find_all("a", href=True)
                if any(kw in (a.get_text(" ", strip=True) + a["href"]).lower()
                       for kw in vacancy_keywords)
            ]

            for a in links:
                try:
                    title = a.get_text(" ", strip=True)
                    if not title or len(title) < 5:
                        continue
                    href = _href(a, BASE_URL)
                    if not href:
                        continue

                    # Infer ministry from surrounding container text
                    parent_text = _text(a.find_parent())
                    company = "Government of Namibia"
                    for kw in ("Ministry", "Office of", "Commission", "Authority",
                               "Board", "Council", "Agency", "Department"):
                        idx = parent_text.find(kw)
                        if idx != -1:
                            company = parent_text[idx:idx + 60].split("\n")[0].strip()
                            break

                    if _save(db, title=title, company=company,
                             source_url=href, source_name=SOURCE):
                        saved += 1
                        log.info("[%s] Saved: %s", SOURCE, title)
                    time.sleep(DELAY)
                except Exception as e:
                    log.warning("[%s] Link parse error: %s", SOURCE, e)

    except Exception as e:
        log.error("[%s] Scrape failed: %s", SOURCE, e)
    finally:
        db.close()
        http.close()

    log.info("[%s] Done — %d jobs saved", SOURCE, saved)
    return saved


# ---------------------------------------------------------------------------
# 21. City of Windhoek
# ---------------------------------------------------------------------------

def scrape_city_windhoek() -> int:
    return _scrape_company(
        "City of Windhoek", "https://www.windhoekcc.org.na",
        ["/vacancies", "/careers", "/jobs", "/municipality/vacancies",
         "/about-us/vacancies", "/"],
    )


# ---------------------------------------------------------------------------
# 22. NamRA — Namibia Revenue Agency
# ---------------------------------------------------------------------------

def scrape_namra() -> int:
    return _scrape_company(
        "NamRA", "https://www.namra.org.na",
        ["/careers", "/vacancies", "/about/careers", "/about-us/vacancies",
         "/join-us", "/"],
    )


# ===========================================================================
# Orchestrator
# ===========================================================================

SCRAPER_REGISTRY = [
    # ── Job boards ──────────────────────────────────────────────────────────
    ("myjob.com.na",              scrape_myjob),
    ("namijob.com",               scrape_namijob),
    ("jobs4na.com",               scrape_jobs4na),
    ("najobs.info",               scrape_najobs),
    ("jobsnamibia.net",           scrape_jobsnamibia),
    ("jobvacanciesinnamibia.com", scrape_jobvacancies),
    # ── Company career pages ────────────────────────────────────────────────
    ("MTC Namibia",               scrape_mtc),
    ("NamPower",                  scrape_nampower),
    ("Bank of Windhoek",          scrape_bank_windhoek),
    ("Nedbank Namibia",           scrape_nedbank),
    ("FNB Namibia",               scrape_fnb),
    ("Bank of Namibia",           scrape_bon),
    ("O&L Group",                 scrape_ol_group),
    ("Namib Mills",               scrape_namib_mills),
    ("Namdeb",                    scrape_namdeb),
    ("Namport",                   scrape_namport),
    ("Gondwana Collection",       scrape_gondwana),
    ("Telecom Namibia",           scrape_telecom),
    ("Paratus Namibia",           scrape_paratus),
    # ── Government portals ──────────────────────────────────────────────────
    ("PSC Namibia",               scrape_psc),
    ("City of Windhoek",          scrape_city_windhoek),
    ("NamRA",                     scrape_namra),
]


def run_all_scrapers() -> dict:
    """Run every scraper in sequence and print a summary table."""
    log.info("=" * 60)
    log.info(
        "NamibJobs — full scrape run started at %s",
        datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"),
    )
    log.info("=" * 60)

    results: dict[str, int] = {}
    for name, fn in SCRAPER_REGISTRY:
        log.info(">>> Scraping %s", name)
        results[name] = fn()
        time.sleep(DELAY)

    col   = 36
    total = sum(results.values())
    bar   = "=" * (col + 18)
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
