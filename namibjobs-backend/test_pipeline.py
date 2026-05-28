"""
End-to-end pipeline test:
  1. Scrape at least 10 jobs from myjob.com.na
  2. Run NLP (skills extraction + embeddings) on all unprocessed jobs
  3. Run recommendation for a sample profile and print top 5 results
"""
import sys
import json
import traceback
from pathlib import Path

# Force UTF-8 output on Windows
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")

sys.path.append(str(Path(__file__).resolve().parent))

PROFILE = (
    "I am a software developer with experience in Python and REST APIs "
    "looking for a full time job in Windhoek"
)
MIN_JOBS = 10
TOP_N = 5

PASS  = "[OK]"
FAIL  = "[FAIL]"
SEP   = "-" * 60


def section(title: str):
    print(f"\n{SEP}\n  {title}\n{SEP}")


# ── Step 0: verify DB connection ──────────────────────────────────────────────
section("Step 0 -- Database connection")
try:
    from database.database import SessionLocal, engine
    from database.models import Job
    with engine.connect() as conn:
        pass
    print(f"{PASS} Connected to database.")
except Exception:
    print(f"{FAIL} Could not connect to the database.")
    print(traceback.format_exc())
    print("\nMake sure DATABASE_URL in .env is correct and PostgreSQL is running.")
    sys.exit(1)


# ── Step 1: scrape ─────────────────────────────────────────────────────────────
section("Step 1 -- Scraper")
try:
    db = SessionLocal()
    before = db.query(Job).count()
    db.close()
    print(f"  Jobs in DB before scrape: {before}")

    from scraper.myjob_scraper import scrape
    scrape()

    db = SessionLocal()
    after = db.query(Job).count()
    db.close()
    added = after - before
    print(f"  Jobs in DB after scrape:  {after}  (+{added} new)")

    if after < MIN_JOBS:
        print(
            f"{FAIL} Only {after} jobs in DB -- need at least {MIN_JOBS}.\n"
            "  The scraper CSS selectors may need updating for the live site.\n"
            "  Open https://www.myjob.com.na in a browser, inspect a job card,\n"
            "  and update CARD_SELECTOR / TITLE_SELECTOR etc. in scraper/myjob_scraper.py."
        )
        sys.exit(1)

    print(f"{PASS} Scrape complete -- {after} jobs available.")
except Exception:
    print(f"{FAIL} Scraper raised an exception:")
    print(traceback.format_exc())
    sys.exit(1)


# ── Step 2: NLP pipeline ───────────────────────────────────────────────────────
section("Step 2 -- NLP pipeline (skills + embeddings)")
try:
    db = SessionLocal()
    pending = db.query(Job).filter(Job.embedding == None).count()  # noqa: E711
    db.close()
    print(f"  Jobs without embeddings: {pending}")

    if pending == 0:
        print(f"{PASS} All jobs already processed -- skipping.")
    else:
        from nlp.process_jobs import run as run_nlp
        run_nlp()

        db = SessionLocal()
        still_pending = db.query(Job).filter(Job.embedding == None).count()  # noqa: E711
        processed = pending - still_pending
        db.close()

        if still_pending > 0:
            print(f"  {FAIL} {still_pending} jobs still have no embedding after processing.")
        print(f"{PASS} NLP complete -- {processed} jobs processed.")
except Exception:
    print(f"{FAIL} NLP pipeline raised an exception:")
    print(traceback.format_exc())
    sys.exit(1)


# ── Step 3: recommendations ────────────────────────────────────────────────────
section("Step 3 -- Recommendations")
try:
    db = SessionLocal()
    with_embeddings = db.query(Job).filter(Job.embedding != None).count()  # noqa: E711
    db.close()

    if with_embeddings == 0:
        print(f"{FAIL} No jobs have embeddings -- cannot run recommendations.")
        sys.exit(1)

    print(f"  Profile: \"{PROFILE}\"\n")

    from nlp.recommender import get_recommendations
    results = get_recommendations(PROFILE, top_n=TOP_N)

    if not results:
        print(f"{FAIL} get_recommendations returned an empty list.")
        sys.exit(1)

    print(f"{PASS} Top {len(results)} matches:\n")
    for rank, job in enumerate(results, 1):
        skills_preview = ", ".join(job["skills"][:4]) if job["skills"] else "N/A"
        print(
            f"  {rank}. {job['match_score']}%  {job['title']}\n"
            f"       Company  : {job['company']}\n"
            f"       Location : {job['location'] or 'N/A'}\n"
            f"       Type     : {job['job_type'] or 'N/A'}\n"
            f"       Skills   : {skills_preview}\n"
            f"       URL      : {job['source_url']}\n"
        )

except Exception:
    print(f"{FAIL} Recommendation function raised an exception:")
    print(traceback.format_exc())
    sys.exit(1)


# ── Summary ────────────────────────────────────────────────────────────────────
section("Result")
print(f"{PASS} All steps passed.\n")
