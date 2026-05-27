from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from database.database import get_db
from database.models import Job
from nlp.recommender import get_recommendations
from api.schemas import JobResponse, RecommendRequest, RecommendResult

router = APIRouter()


@router.get("/health")
def health():
    return {"status": "ok"}


@router.get("/jobs", response_model=list[JobResponse])
def list_jobs(
    location: str | None = Query(default=None, description="Filter by location (case-insensitive, partial match)"),
    job_type: str | None = Query(default=None, description="Filter by job type (e.g. full-time, contract)"),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    query = db.query(Job)

    if location:
        query = query.filter(Job.location.ilike(f"%{location}%"))
    if job_type:
        query = query.filter(Job.job_type.ilike(f"%{job_type}%"))

    return query.offset(skip).limit(limit).all()


@router.get("/jobs/{job_id}", response_model=JobResponse)
def get_job(job_id: int, db: Session = Depends(get_db)):
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found.")
    return job


@router.post("/recommend", response_model=list[RecommendResult])
def recommend(body: RecommendRequest):
    if not body.profile_text.strip():
        raise HTTPException(status_code=422, detail="profile_text must not be empty.")
    try:
        return get_recommendations(body.profile_text)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
