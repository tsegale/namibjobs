import sys
import json
import numpy as np
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))

from nlp.pipeline import embedder
from database.database import SessionLocal
from database.models import Job


def get_recommendations(profile_text: str, top_n: int = 10) -> list[dict]:
    """
    Given a plain-text candidate profile, return the top_n most similar jobs
    from the database ranked by cosine similarity.

    Match score is returned as a percentage (0–100).
    Requires jobs to have embeddings — run nlp/process_jobs.py first.
    """
    if not profile_text or not profile_text.strip():
        raise ValueError("profile_text must not be empty.")

    profile_vec = np.array(
        embedder.encode(profile_text.strip(), normalize_embeddings=True),
        dtype=np.float32,
    )

    db = SessionLocal()
    try:
        jobs = (
            db.query(Job)
            .filter(Job.embedding.isnot(None))
            .all()
        )

        if not jobs:
            return []

        # Stack all job embeddings into a matrix for a single batched dot product
        job_vecs = np.array([job.embedding for job in jobs], dtype=np.float32)

        # cosine similarity = dot product (both sides are L2-normalised)
        scores = job_vecs @ profile_vec  # shape: (n_jobs,)

        top_indices = np.argsort(scores)[::-1][:top_n]

        return [
            {
                "id": jobs[i].id,
                "title": jobs[i].title,
                "company": jobs[i].company,
                "location": jobs[i].location,
                "job_type": jobs[i].job_type,
                "skills": json.loads(jobs[i].skills) if jobs[i].skills else [],
                "source_url": jobs[i].source_url,
                "match_score": round(float(scores[i]) * 100, 2),
            }
            for i in top_indices
        ]
    finally:
        db.close()


if __name__ == "__main__":
    sample_profile = (
        "I am a software developer with 3 years of experience in Python, "
        "FastAPI, and PostgreSQL. I have worked on data pipelines and REST APIs. "
        "Based in Windhoek, Namibia."
    )

    results = get_recommendations(sample_profile)

    print(f"\nTop {len(results)} job matches:\n")
    for rank, job in enumerate(results, 1):
        print(
            f"{rank:>2}. [{job['match_score']}%] {job['title']} @ {job['company']}"
            f"  |  {job['location'] or 'N/A'}  |  {job['source_url']}"
        )
