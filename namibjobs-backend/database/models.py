from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime
from .database import Base


class Job(Base):
    __tablename__ = "jobs"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    company = Column(String(255), nullable=False)
    location = Column(String(255))
    description = Column(Text)
    skills = Column(Text)           # comma-separated or JSON string
    salary = Column(String(100))
    job_type = Column(String(50))   # full-time, part-time, contract, etc.
    source_url = Column(String(500), unique=True, nullable=False)
    source_name = Column(String(100), nullable=False)
    date_scraped = Column(DateTime, default=datetime.utcnow, nullable=False)
