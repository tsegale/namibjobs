"""
NamibJobs — multi-source scraper v3
Confirmed-working sources (produce real data):
  jobs4na.com            — Elementor/WP blog, detail-page job parsing, 5 pages
  recruitment.nampower.com.na — NamPower eRecruitment portal, static HTML
  Bank of Namibia JSON API    — services.bon.com.na (empty when no active vacancies)

Gracefully-failing sources (return 0, log reason):
  najobs.info / jobsnamibia.net  — Cloudflare challenge
  namijob.com                    — Drupal + Solr (JS-rendered, needs Selenium)
  Bank of Windhoek               — SharePoint + JS (needs Selenium)
  NamRA / NamRA                  — SPA (needs Selenium)
  MTC, PSC, City of Windhoek,    — DNS unreachable from this environment
    FNB, Telecom, Paratus, etc.
  Careers24                      — accessible but shows SA jobs, not Namibia
  Jobberman / Gumtree / JP       — DNS unreachable

To enable JS-rendered sites:
  pip install selenium
  Install Chrome + ChromeDriver matching your Chrome version, add to PATH.
"""

import re
import sys
import json
import time
import logging
import warnings
import unicodedata
from datetime import datetime
from pathlib import Path

import requests
from requests.packages.urllib3.exceptions import InsecureRequestWarning
warnings.filterwarnings("ignore", category=InsecureRequestWarning)
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

DELAY = 3   # seconds between page requests

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Encoding": "gzip, deflate",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
}

# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _get(url: str, session: requests.Session, verify: bool = True) -> BeautifulSoup | None:
    try:
        r = session.get(url, headers=HEADERS, timeout=15, verify=verify)
        r.raise_for_status()
        return BeautifulSoup(r.content, "html.parser")
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
# Selenium helper — for JS-rendered sites
# ---------------------------------------------------------------------------

def _get_selenium(url: str, wait_sec: int = 5) -> BeautifulSoup | None:
    """Fetch a JS-rendered page via headless Chrome.
    Returns None gracefully if selenium / ChromeDriver is not available.
    Install: pip install selenium  (ChromeDriver must be in PATH).
    """
    try:
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options
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
        time.sleep(wait_sec)
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
    """Try static fetch; fall back to Selenium if page looks JS-rendered (sparse text)."""
    soup = _get(url, session)
    if soup and len(soup.get_text(" ", strip=True)) > 500:
        return soup
    log.info("Sparse static content at %s — retrying with Selenium", url)
    return _get_selenium(url, wait_sec=wait_sec)


# ---------------------------------------------------------------------------
# Generic single-company career page scraper
# ---------------------------------------------------------------------------

_CARD_SELS = [
    ".vacancy-item", ".vacancy", ".job-vacancy",
    ".career-item", ".career", ".job-item", ".job-listing", ".job",
    ".position-item", ".position", ".opening",
    "article.job", "article.vacancy", "article.position", "article.career",
    "li.vacancy", "li.job", "li.career", "li.position",
    "tr.vacancy", "tr.job", ".careers-item", ".careers-listing",
    ".career-opportunity", ".listing-item",
]
_TITLE_SELS = [
    "h2 a", "h3 a", "h4 a",
    ".job-title a", ".position-title a", ".vacancy-title a", ".title a",
    "h2", "h3", "h4", ".job-title", ".position-title", ".vacancy-title",
    "td.position", "td.title",
]
_LOC_SELS   = [".location", ".job-location", ".vacancy-location",
               "span.location", "td.location", ".city", ".region"]
_DESC_SELS  = [".description", ".job-description", ".vacancy-description",
               ".summary", ".excerpt", ".requirements", "p.description"]
_CLOSE_SELS = [".closing-date", ".deadline", ".expiry", ".expiry-date",
               ".application-deadline", "td.deadline", "span.date"]


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
    verify: bool = True,
) -> int:
    card_sels    = card_sels    or _CARD_SELS
    title_sels   = title_sels   or _TITLE_SELS
    loc_sels     = loc_sels     or _LOC_SELS
    desc_sels    = desc_sels    or _DESC_SELS
    closing_sels = closing_sels or _CLOSE_SELS

    fetch = (lambda u, s: _get_or_js(u, s)) if use_js else (lambda u, s: _get(u, s, verify=verify))
    http  = requests.Session()
    db    = SessionLocal()
    saved = 0

    def _pick(card, sels):
        for sel in sels:
            t = card.select_one(sel)
            if t:
                return t
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
# 1. myjob.com.na  — delegates to dedicated scraper
# ===========================================================================

def scrape_myjob() -> int:
    try:
        return _myjob_scrape() or 0
    except Exception as e:
        log.error("[myjob.com.na] Scrape failed: %s", e)
        return 0


# ===========================================================================
# 2. namijob.com  — Drupal + Solr (JS-rendered, needs Selenium)
# ===========================================================================

def scrape_namijob() -> int:
    SOURCE = "namijob.com"
    BASE   = "https://www.namijob.com"
    SEARCH = f"{BASE}/job-vacancies-search-namibia"

    http = requests.Session()
    db   = SessionLocal()
    saved = 0

    try:
        log.info("[%s] Starting scrape", SOURCE)
        # Static fetch returns facets but no job rows (Solr AJAX). Try Selenium.
        soup = _get_selenium(SEARCH, wait_sec=6) if True else None
        if not soup:
            log.warning("[%s] JS rendering unavailable — 0 results (install selenium + ChromeDriver)", SOURCE)
            return 0

        # Drupal views rows
        rows = (
            soup.select(".views-row") or
            soup.select("article.node--type-job-offer") or
            soup.select(".node--type-job-offer")
        )
        if not rows:
            log.warning("[%s] Selenium loaded page but no job rows found — selectors may need updating", SOURCE)
            return 0

        log.info("[%s] Found %d rows", SOURCE, len(rows))

        for row in rows:
            try:
                title_tag = (
                    row.select_one("h2 a") or row.select_one("h3 a") or
                    row.select_one(".field--name-title a") or row.select_one("a")
                )
                title   = _text(title_tag)
                url     = _href(title_tag, BASE)
                company = _text(
                    row.select_one(".field--name-field-company") or
                    row.select_one(".company")
                ) or "Unknown"
                location = _text(row.select_one(".field--name-field-location") or
                                  row.select_one(".location")) or None

                if not title or not url:
                    continue

                if _save(db, title=title, company=company, location=location,
                         source_url=url, source_name=SOURCE):
                    saved += 1
                    log.info("[%s] Saved: %s @ %s", SOURCE, title, company)
                time.sleep(DELAY)

            except Exception as e:
                log.warning("[%s] Row parse error: %s", SOURCE, e)

    except Exception as e:
        log.error("[%s] Scrape failed: %s", SOURCE, e)
    finally:
        db.close()
        http.close()

    log.info("[%s] Done — %d jobs saved", SOURCE, saved)
    return saved


# ===========================================================================
# 3. jobs4na.com  — Elementor/WordPress blog with per-company job articles
#    Listing page:  article.elementor-post  >  h3.elementor-post__title a
#    Detail page:   .entry-content  — jobs separated by "More job details"
#    Pagination:    /page/2/, /page/3/ … up to MAX_LISTING_PAGES
# ===========================================================================

def _jobs4na_company_from_title(title: str) -> str:
    """Extract company name from a jobs4na article title."""
    t = re.sub(r",?\s*(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\w*\s+\d{4}", "", title)
    t = re.sub(r"\s*[-–]\s*Daily Updates.*$", "", t, flags=re.IGNORECASE)
    for pat in [
        r"New Jobs\s*:\s*(.+?)\s+(?:is hiring|are hiring|vacancies)",
        r"New Jobs?\s+[-–:]\s*(.+?)\s+(?:is|are|Jobs|Vacanc)",
        r"^(.+?)\s+(?:is hiring|are hiring|Vacancies|Jobs)[\s,!]",
        r"^(.+?)\s+Vacanc(?:y|ies)",
    ]:
        m = re.match(pat, t, re.IGNORECASE)
        if m:
            return m.group(1).strip()
    # Fallback: first 3 capitalised words
    words = t.split()
    caps = [w for w in words[:4] if w and w[0].isupper() and len(w) > 1]
    return " ".join(caps[:3]) if caps else "Various Namibian Companies"


def _jobs4na_parse_detail(content_text: str, company: str, article_url: str, db, source_name: str) -> int:
    """Parse individual job entries from a jobs4na detail page content block."""
    saved = 0
    # Full delimiter used on jobs4na.com
    DELIM = "More job details & Application >>>"
    chunks = content_text.split(DELIM)
    if len(chunks) < 2:
        # Try shorter fallback delimiter
        chunks = content_text.split("More job details")
    if len(chunks) < 2:
        # No structured jobs — store whole article as one entry
        title = content_text[:120].split("\n")[0].strip()
        if title and len(title) > 5:
            if _save(db, title=title, company=company,
                     description=content_text[:500],
                     source_url=article_url, source_name=source_name):
                saved += 1
        return saved

    for chunk in chunks[:-1]:   # last chunk is trailing text after final delimiter
        lines = [l.strip() for l in chunk.split("\n") if l.strip()]
        if not lines:
            continue

        # First non-empty line is the job title
        job_title = lines[0]
        # Skip lines that are obviously not a job title
        if len(job_title) < 4 or len(job_title) > 160:
            continue
        if job_title.lower().startswith(("these", "click", "more", "advertisement", "share", "&", "application", ">>>")):
            continue
        if ">>>" in job_title or job_title.lower().startswith("swakop uranium is hiring"):
            continue

        # Extract closing date and description
        closing = ""
        desc_lines = []
        for line in lines[1:]:
            m = re.search(r"[Cc]losing [Dd]ate\s*:?\s*(.+?)(?:\)|\Z)", line)
            if m:
                closing = m.group(1).strip()
            elif re.search(r"(PURPOSE|RESPONSIBILITIES|REQUIREMENTS|QUALIFICATION|DUTIES)", line, re.IGNORECASE):
                desc_lines.append(line)
            elif len(line) > 15 and not line.startswith("("):
                desc_lines.append(line)

        description = " ".join(desc_lines[:3])
        if closing:
            description = (description + f" Closing: {closing}").strip()

        # Unique URL per job: article URL + title slug
        source_url = f"{article_url}#{_slug(job_title)}"

        if _save(db, title=job_title, company=company,
                 description=description or None,
                 source_url=source_url, source_name=source_name):
            saved += 1
            log.info("[jobs4na.com] Saved: %s @ %s", job_title, company)

    return saved


def scrape_jobs4na() -> int:
    SOURCE    = "jobs4na.com"
    BASE      = "https://jobs4na.com"
    MAX_PAGES = 5

    http = requests.Session()
    db   = SessionLocal()
    saved = 0

    try:
        log.info("[%s] Starting scrape (up to %d pages)", SOURCE, MAX_PAGES)

        for page_num in range(1, MAX_PAGES + 1):
            url = BASE + "/" if page_num == 1 else f"{BASE}/page/{page_num}/"
            soup = _get(url, http)
            if not soup:
                log.warning("[%s] Could not fetch page %d", SOURCE, page_num)
                break

            articles = soup.select("article.elementor-post")
            if not articles:
                log.info("[%s] No articles on page %d — stopping pagination", SOURCE, page_num)
                break

            log.info("[%s] Page %d: %d articles", SOURCE, page_num, len(articles))

            for article in articles:
                try:
                    title_tag = article.select_one("h3.elementor-post__title a")
                    if not title_tag:
                        title_tag = article.select_one("h2 a, h3 a, .elementor-post__title a")
                    if not title_tag:
                        continue

                    article_title = _text(title_tag)
                    article_url   = title_tag.get("href", "").strip()
                    if not article_url:
                        continue

                    company = _jobs4na_company_from_title(article_title)

                    time.sleep(DELAY)
                    detail = _get(article_url, http)
                    if not detail:
                        continue

                    content = (
                        detail.select_one(".entry-content") or
                        detail.select_one(".elementor-widget-theme-post-content") or
                        detail.select_one("article")
                    )
                    content_text = content.get_text("\n", strip=True) if content else ""

                    if "More job details" in content_text:
                        n = _jobs4na_parse_detail(content_text, company, article_url, db, SOURCE)
                        saved += n
                    else:
                        # Roundup/advice article — skip
                        log.debug("[%s] Skipping non-structured article: %s", SOURCE, article_title[:60])

                except Exception as e:
                    log.warning("[%s] Article error: %s", SOURCE, e)

            time.sleep(DELAY)

    except Exception as e:
        log.error("[%s] Scrape failed: %s", SOURCE, e)
    finally:
        db.close()
        http.close()

    log.info("[%s] Done — %d jobs saved", SOURCE, saved)
    return saved


# ===========================================================================
# 4. najobs.info — Cloudflare-protected
# ===========================================================================

def scrape_najobs() -> int:
    SOURCE = "najobs.info"
    try:
        r = requests.get("https://najobs.info/", headers=HEADERS, timeout=10)
        if "moment" in r.text.lower() or "cloudflare" in r.text.lower() or r.status_code == 403:
            log.warning("[%s] Cloudflare challenge detected — 0 results", SOURCE)
            return 0
        # If it ever becomes accessible, fall through to generic scraping
        return _scrape_company(SOURCE, "https://najobs.info", ["/", "/jobs/", "/vacancies/"])
    except Exception as e:
        log.error("[%s] Failed: %s", SOURCE, e)
        return 0


# ===========================================================================
# 5. jobsnamibia.net — Cloudflare-protected
# ===========================================================================

def scrape_jobsnamibia() -> int:
    SOURCE = "jobsnamibia.net"
    try:
        r = requests.get("https://www.jobsnamibia.net/", headers=HEADERS, timeout=10)
        if "moment" in r.text.lower() or "cloudflare" in r.text.lower() or r.status_code == 403:
            log.warning("[%s] Cloudflare challenge detected — 0 results", SOURCE)
            return 0
        return _scrape_company(SOURCE, "https://www.jobsnamibia.net", ["/", "/jobs/", "/vacancies/"])
    except Exception as e:
        log.error("[%s] Failed: %s", SOURCE, e)
        return 0


# ===========================================================================
# 6. jobvacanciesinnamibia.com — WordPress blog (advice articles, not job listings)
# ===========================================================================

def scrape_jobvacancies() -> int:
    SOURCE = "jobvacanciesinnamibia.com"
    BASE   = "https://jobvacanciesinnamibia.com"

    http = requests.Session()
    db   = SessionLocal()
    saved = 0

    try:
        log.info("[%s] Starting scrape", SOURCE)
        soup = _get(f"{BASE}/category/latest-vacancies/", http)
        if not soup:
            soup = _get(f"{BASE}/", http)
        if not soup:
            log.warning("[%s] Could not reach site", SOURCE)
            return 0

        articles = soup.select("article.post")
        if not articles:
            articles = soup.select("article")
        log.info("[%s] Found %d posts", SOURCE, len(articles))

        for article in articles:
            try:
                title_tag = (
                    article.select_one("h2.entry-title a") or
                    article.select_one("h1.entry-title a") or
                    article.select_one("h2 a") or article.select_one("h3 a")
                )
                title = _text(title_tag)
                url   = _href(title_tag, BASE)
                if not title or not url:
                    continue

                # Skip advice/guide articles and non-Namibian jobs
                skip_kw = ("how to", "guide", "tips", "germany", "visa", "canada", "canadian",
                           "interview", "cv", "salary", "labour act", "learnerships",
                           "usa", "united states", "us resort", "uk ", "australia",
                           "seasonal harvest", "critical worker", "top 10", "in demand",
                           "pathway to", "hidden", "mortenson", "dhl warehouse")
                if any(kw in title.lower() for kw in skip_kw):
                    log.debug("[%s] Skipping advice/non-Namibia article: %s", SOURCE, title[:60])
                    continue
                # Only save if title sounds like a real job (has job-like keywords)
                job_kw = ("officer", "manager", "analyst", "engineer", "coordinator",
                          "assistant", "clerk", "technician", "specialist", "director",
                          "administrator", "developer", "consultant", "driver", "supervisor",
                          "accountant", "nurse", "doctor", "teacher", "lecturer",
                          "mechanic", "plumber", "electrician", "intern", "graduate",
                          "vacancies", "vacancy", "hiring", "recruitment", "position")
                if not any(kw in title.lower() for kw in job_kw):
                    log.debug("[%s] Skipping non-job article: %s", SOURCE, title[:60])
                    continue

                company = _text(
                    article.select_one(".company") or article.select_one(".employer")
                ) or "Various Namibian Employers"

                desc = _text(
                    article.select_one(".entry-summary") or
                    article.select_one(".entry-content p") or
                    article.select_one("p")
                ) or None

                if _save(db, title=title, company=company, description=desc,
                         source_url=url, source_name=SOURCE):
                    saved += 1
                    log.info("[%s] Saved: %s", SOURCE, title)
                time.sleep(DELAY)

            except Exception as e:
                log.warning("[%s] Article error: %s", SOURCE, e)

    except Exception as e:
        log.error("[%s] Scrape failed: %s", SOURCE, e)
    finally:
        db.close()
        http.close()

    log.info("[%s] Done — %d jobs saved", SOURCE, saved)
    return saved


# ===========================================================================
# 7. NamPower — recruitment.nampower.com.na (dedicated eRecruitment portal)
#    Card:     .job-list.main-background
#    Title:    div.hidden-xs.hidden-sm  (first occurrence)
#    URL:      a[href=/Jobs/ViewJob/NNN]
#    Meta:     .meta-tag.hidden-xs.hidden-sm  — "Location  Closing Date: DD/MM/YYYY"
# ===========================================================================

def scrape_nampower() -> int:
    SOURCE = "NamPower"
    BASE   = "https://recruitment.nampower.com.na"

    http = requests.Session()
    db   = SessionLocal()
    saved = 0

    try:
        log.info("[%s] Starting scrape", SOURCE)
        soup = _get(f"{BASE}/", http)
        if not soup:
            log.warning("[%s] Could not reach %s", SOURCE, BASE)
            return 0

        jobs = soup.select(".job-list")
        log.info("[%s] Found %d listings", SOURCE, len(jobs))

        for job in jobs:
            try:
                # Title is in the first .hidden-xs.hidden-sm div (desktop view)
                title_el = job.select_one(".hidden-xs.hidden-sm")
                title    = _text(title_el)
                if not title:
                    continue

                # Link to detail page
                link_el  = job.find("a", href=lambda h: h and "/Jobs/ViewJob/" in h)
                url      = (BASE + link_el["href"]) if link_el else f"{BASE}/#{_slug(title)}"

                # Location + closing date from meta-tag block
                meta_el = job.select_one(".meta-tag.hidden-xs.hidden-sm, .job-tag")
                meta    = _text(meta_el) if meta_el else ""

                # "Eros Airport, Windhoek, Namibia Closing Date: 03/06/2026 ..."
                closing_m  = re.search(r"Closing Date:\s*([\d/]+)", meta)
                closing    = closing_m.group(1) if closing_m else ""
                location   = meta.split("Closing Date")[0].strip() or "Namibia"
                description = f"Closing Date: {closing}" if closing else None

                if _save(db, title=title, company=SOURCE, location=location,
                         description=description, source_url=url, source_name=SOURCE):
                    saved += 1
                    log.info("[%s] Saved: %s", SOURCE, title)
                time.sleep(DELAY)

            except Exception as e:
                log.warning("[%s] Job parse error: %s", SOURCE, e)

    except Exception as e:
        log.error("[%s] Scrape failed: %s", SOURCE, e)
    finally:
        db.close()
        http.close()

    log.info("[%s] Done — %d jobs saved", SOURCE, saved)
    return saved


# ===========================================================================
# 8. Bank of Namibia — JSON API
#    Endpoint: https://services.bon.com.na/nieis-web-scraper/getjobs
#    Returns:  [{title, url, closingDate}, ...]   (empty when no active vacancies)
# ===========================================================================

def scrape_bon() -> int:
    SOURCE  = "Bank of Namibia"
    API_URL = "https://services.bon.com.na/nieis-web-scraper/getjobs"
    BASE    = "https://www.bon.com.na"

    http = requests.Session()
    db   = SessionLocal()
    saved = 0

    try:
        log.info("[%s] Querying JSON API", SOURCE)
        r = http.get(API_URL, headers={**HEADERS, "Accept": "application/json"},
                     timeout=15)
        r.raise_for_status()
        vacancies = r.json()

        if not vacancies:
            log.info("[%s] API returned 0 vacancies (none currently advertised)", SOURCE)
            return 0

        log.info("[%s] API returned %d vacancies", SOURCE, len(vacancies))

        for v in vacancies:
            try:
                title = (v.get("title") or "").strip()
                if not title:
                    continue

                raw_url = v.get("url") or ""
                url = raw_url if raw_url.startswith("http") else (BASE + raw_url if raw_url else f"{BASE}/vacancies#{_slug(title)}")

                closing = v.get("closingDate") or v.get("closing_date") or ""
                desc    = f"Closing: {closing}" if closing else None

                if _save(db, title=title, company=SOURCE, description=desc,
                         source_url=url, source_name=SOURCE):
                    saved += 1
                    log.info("[%s] Saved: %s", SOURCE, title)
                time.sleep(1)

            except Exception as e:
                log.warning("[%s] Entry parse error: %s", SOURCE, e)

    except Exception as e:
        log.error("[%s] Scrape failed: %s", SOURCE, e)
    finally:
        db.close()
        http.close()

    log.info("[%s] Done — %d jobs saved", SOURCE, saved)
    return saved


# ===========================================================================
# 9–21. Company career pages via generic factory
# ===========================================================================

def scrape_mtc() -> int:
    return _scrape_company(
        "MTC Namibia", "https://www.mtc.com.na",
        ["/corporate/careers", "/careers", "/vacancies", "/jobs"],
        verify=False,
    )

def scrape_bank_windhoek() -> int:
    # SharePoint site — /Pages/Careers.aspx loads vacancies via JS
    return _scrape_company(
        "Bank of Windhoek", "https://www.bankwindhoek.com.na",
        ["/Pages/Careers.aspx", "/careers", "/vacancies"],
        use_js=True,
    )

def scrape_nedbank() -> int:
    return _scrape_company(
        "Nedbank Namibia", "https://www.nedbank.com.na",
        ["/careers", "/vacancies", "/about/careers", "/"],
        use_js=True,
    )

def scrape_fnb() -> int:
    # FNB uses an external portal page; the careers link is /fnb-careers/index.html
    return _scrape_company(
        "FNB Namibia", "https://www.fnbnamibia.com.na",
        ["/fnb-careers/index.html", "/careers", "/vacancies", "/about-fnb/careers"],
        use_js=False,
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
        verify=False,
    )

def scrape_namdeb() -> int:
    return _scrape_company(
        "Namdeb", "https://www.namdeb.com",
        ["/careers", "/vacancies", "/people", "/about/careers", "/"],
    )

def scrape_namport() -> int:
    SOURCE = "Namport"
    BASE = "https://www.namport.com.na"
    URL = f"{BASE}/careers/28/"
    http = requests.Session()
    db = SessionLocal()
    saved = 0
    try:
        log.info("[%s] Starting scrape", SOURCE)
        soup = _get(URL, http, verify=False)
        if not soup:
            log.warning("[%s] Could not reach site", SOURCE)
            return 0
        header_seen = False
        for row in soup.select("table tr"):
            cells = row.find_all(["td", "th"])
            text = " ".join(c.get_text(strip=True) for c in cells)
            if "Job Title" in text:
                header_seen = True
                continue
            if header_seen and cells and len(cells) >= 3:
                title = cells[0].get_text(strip=True)
                deadline_text = cells[1].get_text(strip=True) if len(cells) > 1 else ""
                link_tag = row.find("a", href=True)
                link = (BASE + "/" + link_tag["href"].lstrip("/")) if link_tag else URL
                if not title:
                    continue
                closing = None
                m = re.search(r"(\d{2}-\w{3}-\d{4})", deadline_text)
                if m:
                    try:
                        closing = datetime.strptime(m.group(1), "%d-%b-%Y").date()
                    except ValueError:
                        pass
                if _save(db, title=title, company=SOURCE, location="Namibia",
                         source_url=link, source_name=SOURCE):
                    saved += 1
                    log.info("[%s] Saved: %s", SOURCE, title)
        log.info("[%s] Done — %d jobs saved", SOURCE, saved)
        return saved
    finally:
        db.close()

def scrape_gondwana() -> int:
    return _scrape_company(
        "Gondwana Collection", "https://www.gondwana-collection.com",
        ["/careers", "/jobs", "/vacancies", "/work-with-us", "/join-us", "/"],
    )

def scrape_telecom() -> int:
    SOURCE = "Telecom Namibia"
    URL = "https://www.telecom.na/vacancies"
    http = requests.Session()
    db = SessionLocal()
    saved = 0
    try:
        log.info("[%s] Starting scrape", SOURCE)
        soup = _get(URL, http, verify=False)
        if not soup:
            log.warning("[%s] Could not reach site", SOURCE)
            return 0
        item = soup.select_one(".item-page") or soup.select_one("article") or soup.body
        if not item:
            log.warning("[%s] No content block found", SOURCE)
            return 0
        text = item.get_text("\n", strip=True)
        lines = [l.strip() for l in text.split("\n") if l.strip()]
        # Each job is an ALL-CAPS title followed by "CLOSING DATE:" line
        for i, line in enumerate(lines):
            if not line.isupper() or len(line) < 5 or line.startswith("CLOSING"):
                continue
            if any(noise in line for noise in ["PRINT", "EMAIL", "VACANCIES", "MENU", "HOME"]):
                continue
            title = line
            closing = None
            for j in range(i + 1, min(i + 4, len(lines))):
                m = re.search(r"(\d{1,2}\s+\w+\s+\d{4})", lines[j], re.IGNORECASE)
                if m:
                    for fmt in ["%d %B %Y", "%d %b %Y"]:
                        try:
                            closing = datetime.strptime(m.group(1), fmt).date()
                            break
                        except ValueError:
                            pass
                    break
            source_url = f"{URL}#{_slug(title)}"
            if _save(db, title=title, company=SOURCE, location="Namibia",
                     source_url=source_url, source_name=SOURCE):
                saved += 1
                log.info("[%s] Saved: %s", SOURCE, title)
        log.info("[%s] Done — %d jobs saved", SOURCE, saved)
        return saved
    finally:
        db.close()

def scrape_paratus() -> int:
    return _scrape_company(
        "Paratus Namibia", "https://www.paratus.com.na",
        ["/careers", "/vacancies", "/about/careers", "/about-us/vacancies", "/"],
        verify=False,
    )


# ===========================================================================
# 22. PSC Namibia
# ===========================================================================

def scrape_psc() -> int:
    SOURCE   = "PSC Namibia"
    BASE_URL = "https://www.psc.gov.na"
    PATHS    = ["/vacancy-circulars", "/vacancies", "/circulars", "/"]

    http = requests.Session()
    db   = SessionLocal()
    saved = 0

    try:
        log.info("[%s] Starting scrape", SOURCE)
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
            log.warning("[%s] Could not reach site", SOURCE)
            return 0

        cards = (
            soup.select(".vacancy-circular") or soup.select(".vacancy-item") or
            soup.select("article.vacancy") or soup.select("tr.vacancy")
        )
        links = []
        if not cards:
            vacancy_kw = ("vacant", "circular", "position", "vacancy", "post")
            links = [
                a for a in soup.find_all("a", href=True)
                if any(kw in (a.get_text(" ", strip=True) + a["href"]).lower()
                       for kw in vacancy_kw)
            ]

        targets = cards or links
        log.info("[%s] Found %d items", SOURCE, len(targets))

        for item in targets:
            try:
                if item.name == "a":
                    title = item.get_text(" ", strip=True)
                    href  = _href(item, BASE_URL)
                    company = "Government of Namibia"
                else:
                    title_tag = (
                        item.select_one("h2 a") or item.select_one("h3 a") or
                        item.select_one(".title a") or item.select_one("a")
                    )
                    title   = _text(title_tag)
                    href    = _href(title_tag, BASE_URL)
                    company = _text(item.select_one(".ministry,.department,.institution")) or "Government of Namibia"

                if not title or len(title) < 5:
                    continue
                if not href:
                    href = f"{page_url}#{_slug(title)}"

                if _save(db, title=title, company=company,
                         source_url=href, source_name=SOURCE):
                    saved += 1
                    log.info("[%s] Saved: %s", SOURCE, title)
                time.sleep(DELAY)

            except Exception as e:
                log.warning("[%s] Item parse error: %s", SOURCE, e)

    except Exception as e:
        log.error("[%s] Scrape failed: %s", SOURCE, e)
    finally:
        db.close()
        http.close()

    log.info("[%s] Done — %d jobs saved", SOURCE, saved)
    return saved


def scrape_city_windhoek() -> int:
    SOURCE = "City of Windhoek"
    URL = "https://cityofwindhoek.erecruit.co/candidateapp/Jobs/Browse"
    http = requests.Session()
    db = SessionLocal()
    saved = 0
    try:
        log.info("[%s] Starting scrape", SOURCE)
        soup = _get(URL, http)
        if not soup:
            log.warning("[%s] Could not reach erecruit portal", SOURCE)
            return 0
        # eRecruit renders jobs in table rows or job-item divs
        for row in soup.select("tr, .job-item, .vacancy-item"):
            link_tag = row.find("a", href=True)
            if not link_tag:
                continue
            title = link_tag.get_text(strip=True)
            # Skip category rows like "Engineering (0)"
            if not title or len(title) < 4 or re.search(r"\(\d+\)\s*$", title):
                continue
            href = link_tag["href"]
            if "Browse" in href or "Category" in href:
                continue
            job_url = ("https://cityofwindhoek.erecruit.co" + href
                       if href.startswith("/") else href)
            closing = None
            cells = row.find_all(["td", "th"])
            for c in cells:
                m = re.search(r"(\d{4}-\d{2}-\d{2}|\d{2}/\d{2}/\d{4})", c.get_text())
                if m:
                    for fmt in ["%Y-%m-%d", "%d/%m/%Y"]:
                        try:
                            closing = datetime.strptime(m.group(1), fmt).date()
                            break
                        except ValueError:
                            pass
            if _save(db, title=title, company=SOURCE, location="Windhoek, Namibia",
                     source_url=job_url, source_name=SOURCE):
                saved += 1
                log.info("[%s] Saved: %s", SOURCE, title)
        log.info("[%s] Done — %d jobs saved", SOURCE, saved)
        return saved
    finally:
        db.close()


def scrape_namra() -> int:
    # NamRA is a SPA — needs Selenium
    return _scrape_company(
        "NamRA", "https://www.namra.org.na",
        ["/careers", "/vacancies", "/about/careers", "/"],
        use_js=True,
    )


# ===========================================================================
# New job boards (4 requested)
# ===========================================================================

# ---------------------------------------------------------------------------
# 23. Careers24 Namibia
#     NOTE: careers24.com is a South African board. The /jobs/in-namibia URL
#     currently serves SA jobs only. Scraper runs but jobs may not be Namibia-
#     specific. Filter: only save cards whose location contains "Namibia".
# ---------------------------------------------------------------------------

def scrape_careers24() -> int:
    SOURCE = "Careers24 Namibia"
    BASE   = "https://www.careers24.com"
    URL    = f"{BASE}/jobs/in-namibia/"

    http = requests.Session()
    db   = SessionLocal()
    saved = 0

    try:
        log.info("[%s] Starting scrape", SOURCE)
        soup = _get(URL, http)
        if not soup:
            log.warning("[%s] Could not reach site", SOURCE)
            return 0

        cards = soup.select(".job-card")
        log.info("[%s] Found %d cards", SOURCE, len(cards))

        for card in cards:
            try:
                title_tag = card.select_one("[data-control=vacancy-title] h2") or card.select_one("h2")
                title = _text(title_tag)
                if not title:
                    continue

                link_tag = card.select_one("[data-control=vacancy-title]")
                href     = link_tag.get("href", "") if link_tag else ""
                url      = href if href.startswith("http") else BASE + href
                if not url or url == BASE:
                    continue

                items    = card.select("li")
                location = _text(items[0]) if items else None
                job_type = _text(items[1]) if len(items) > 1 else None

                # Only keep Namibia-specific jobs
                if location and "Namibia" not in location and "Windhoek" not in location:
                    log.debug("[%s] Skipping non-Namibian job: %s (%s)", SOURCE, title, location)
                    continue

                company = _text(card.select_one(".company-name,.recruiter-name,[class*=company]")) or "Unknown"
                desc    = f"Job Type: {job_type}" if job_type else None

                if _save(db, title=title, company=company, location=location,
                         description=desc, source_url=url, source_name=SOURCE):
                    saved += 1
                    log.info("[%s] Saved: %s @ %s", SOURCE, title, location)
                time.sleep(DELAY)

            except Exception as e:
                log.warning("[%s] Card error: %s", SOURCE, e)

    except Exception as e:
        log.error("[%s] Scrape failed: %s", SOURCE, e)
    finally:
        db.close()
        http.close()

    log.info("[%s] Done — %d jobs saved", SOURCE, saved)
    return saved


# ---------------------------------------------------------------------------
# 24. Job Placements Namibia
# ---------------------------------------------------------------------------

def scrape_jobplacements() -> int:
    return _scrape_company(
        "Job Placements Namibia", "https://www.jobplacements.com",
        ["/jobs/namibia", "/namibia", "/jobs", "/"],
    )


# ---------------------------------------------------------------------------
# 25. Jobberman Namibia — DNS unreachable; graceful 0
# ---------------------------------------------------------------------------

def scrape_jobberman() -> int:
    SOURCE = "Jobberman Namibia"
    try:
        soup = _get("https://namibia.jobberman.com", requests.Session())
        if not soup:
            log.warning("[%s] Site unreachable — 0 results", SOURCE)
            return 0
        return _scrape_company(
            SOURCE, "https://namibia.jobberman.com",
            ["/jobs", "/vacancies", "/"],
        )
    except Exception as e:
        log.error("[%s] Failed: %s", SOURCE, e)
        return 0


# ---------------------------------------------------------------------------
# 26. Gumtree Namibia — DNS unreachable; graceful 0
# ---------------------------------------------------------------------------

def scrape_gumtree() -> int:
    SOURCE = "Gumtree Namibia"
    BASE   = "https://www.gumtree.com.na"
    try:
        soup = _get(f"{BASE}/jobs", requests.Session())
        if not soup:
            log.warning("[%s] Site unreachable — 0 results", SOURCE)
            return 0

        cards = (
            soup.select(".listing-cards article") or
            soup.select("article.listing") or
            soup.select(".view-advert")
        )
        if not cards:
            log.warning("[%s] No job cards found", SOURCE)
            return 0

        http = requests.Session()
        db   = SessionLocal()
        saved = 0

        for card in cards:
            try:
                title_tag = card.select_one("h2 a, h3 a, .listing-title a")
                title = _text(title_tag)
                url   = _href(title_tag, BASE)
                if not title or not url:
                    continue
                company = _text(card.select_one(".seller-name,.ad-name")) or "Unknown"
                if _save(db, title=title, company=company, source_url=url, source_name=SOURCE):
                    saved += 1
                    log.info("[%s] Saved: %s", SOURCE, title)
                time.sleep(DELAY)
            except Exception as e:
                log.warning("[%s] Card error: %s", SOURCE, e)

        db.close()
        http.close()
        log.info("[%s] Done — %d jobs saved", SOURCE, saved)
        return saved

    except Exception as e:
        log.error("[%s] Failed: %s", SOURCE, e)
        return 0


# ===========================================================================
# Orchestrator
# ===========================================================================

SCRAPER_REGISTRY = [
    # ── Confirmed working ───────────────────────────────────────────────────
    ("myjob.com.na",              scrape_myjob),
    ("jobs4na.com",               scrape_jobs4na),
    ("NamPower",                  scrape_nampower),
    ("Bank of Namibia",           scrape_bon),
    # ── May work with Selenium ──────────────────────────────────────────────
    ("namijob.com",               scrape_namijob),
    ("Bank of Windhoek",          scrape_bank_windhoek),
    ("Nedbank Namibia",           scrape_nedbank),
    ("FNB Namibia",               scrape_fnb),
    ("Telecom Namibia",           scrape_telecom),
    ("NamRA",                     scrape_namra),
    # ── May work (static, env-dependent) ───────────────────────────────────
    ("jobvacanciesinnamibia.com", scrape_jobvacancies),
    ("MTC Namibia",               scrape_mtc),
    ("O&L Group",                 scrape_ol_group),
    ("Namib Mills",               scrape_namib_mills),
    ("Namdeb",                    scrape_namdeb),
    ("Namport",                   scrape_namport),
    ("Gondwana Collection",       scrape_gondwana),
    ("Paratus Namibia",           scrape_paratus),
    ("PSC Namibia",               scrape_psc),
    ("City of Windhoek",          scrape_city_windhoek),
    # ── Cloudflare-blocked ──────────────────────────────────────────────────
    ("najobs.info",               scrape_najobs),
    ("jobsnamibia.net",           scrape_jobsnamibia),
    # ── New job boards ──────────────────────────────────────────────────────
    ("Careers24 Namibia",         scrape_careers24),
    ("Job Placements Namibia",    scrape_jobplacements),
    ("Jobberman Namibia",         scrape_jobberman),
    ("Gumtree Namibia",           scrape_gumtree),
]


def run_all_scrapers() -> dict:
    """Run every scraper and print a summary table."""
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
