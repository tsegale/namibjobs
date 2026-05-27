import json
from datetime import datetime
from pydantic import BaseModel, field_validator


class JobResponse(BaseModel):
    id: int
    title: str
    company: str
    location: str | None
    description: str | None
    skills: list[str]
    salary: str | None
    job_type: str | None
    source_url: str
    source_name: str
    date_scraped: datetime

    @field_validator("skills", mode="before")
    @classmethod
    def parse_skills(cls, v):
        if isinstance(v, list):
            return v
        if isinstance(v, str):
            try:
                return json.loads(v)
            except (ValueError, TypeError):
                return [s.strip() for s in v.split(",") if s.strip()]
        return []

    model_config = {"from_attributes": True}


class RecommendRequest(BaseModel):
    profile_text: str


class RecommendResult(BaseModel):
    id: int
    title: str
    company: str
    location: str | None
    job_type: str | None
    skills: list[str]
    source_url: str
    match_score: float
