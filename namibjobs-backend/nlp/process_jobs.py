"""
Processes all jobs in the database that are missing skills, job_type, or embedding.
Run with: python nlp/process_jobs.py
"""
import sys
import json
import logging
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))

from database.database import SessionLocal
from database.models import Job
from nlp.pipeline import process_description

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger(__name__)


def needs_processing(job: Job) -> bool:
    return job.description and (
        job.embedding is None
        or job.skills is None
        or job.job_type is None
    )


def run():
    db = SessionLocal()
    try:
        jobs = db.query(Job).all()
        pending = [j for j in jobs if needs_processing(j)]
        log.info("%d jobs to process (out of %d total).", len(pending), len(jobs))

        for i, job in enumerate(pending, 1):
            log.info("[%d/%d] Processing: %s", i, len(pending), job.title)
            try:
                result = process_description(job.description)

                job.skills = json.dumps(result["skills"])
                job.embedding = result["embedding"]

                # Only overwrite location/job_type if not already set
                if not job.location and result["location"]:
                    job.location = result["location"]
                if not job.job_type and result["job_type"]:
                    job.job_type = result["job_type"]

                db.commit()
                log.info(
                    "  skills=%s | type=%s | location=%s | embedding_dims=%d",
                    result["skills"][:3],
                    result["job_type"],
                    result["location"],
                    len(result["embedding"]) if result["embedding"] else 0,
                )
            except Exception as e:
                db.rollback()
                log.error("  Failed on job id=%d: %s", job.id, e)

    finally:
        db.close()

    log.info("Done.")


if __name__ == "__main__":
    run()
