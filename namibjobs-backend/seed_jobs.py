"""
Seeds the database with realistic mock Namibian job listings for testing.
Safe to run multiple times -- skips duplicates via source_url unique constraint.
"""
import sys
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).resolve().parent))

from database.database import SessionLocal
from database.models import Job
from sqlalchemy.exc import IntegrityError

MOCK_JOBS = [
    {
        "title": "Software Developer",
        "company": "Namibia Breweries Limited",
        "location": "Windhoek",
        "description": (
            "We are looking for a full-time Software Developer to join our IT team in Windhoek. "
            "You will design and maintain internal business applications using Python, FastAPI, and PostgreSQL. "
            "Requirements: 3+ years experience with Python, REST API development, SQL databases. "
            "Experience with Docker and Git is a plus. Strong communication and teamwork skills required."
        ),
        "job_type": "full-time",
        "salary": "N$25,000 - N$35,000",
        "source_url": "https://www.myjob.com.na/jobs/software-developer-nbl-001",
        "source_name": "myjob.com.na",
    },
    {
        "title": "Data Analyst",
        "company": "Bank Windhoek",
        "location": "Windhoek",
        "description": (
            "Bank Windhoek seeks a Data Analyst to support our business intelligence team. "
            "You will analyse financial data, build dashboards in Power BI, and write SQL queries. "
            "Requirements: degree in Statistics, Mathematics or Computer Science. "
            "Proficiency in Excel, Python or R, and SQL. Experience with Tableau or Power BI preferred. "
            "Full-time permanent position based in Windhoek."
        ),
        "job_type": "full-time",
        "salary": "N$20,000 - N$28,000",
        "source_url": "https://www.myjob.com.na/jobs/data-analyst-bw-002",
        "source_name": "myjob.com.na",
    },
    {
        "title": "IT Systems Administrator",
        "company": "Telecom Namibia",
        "location": "Windhoek",
        "description": (
            "Telecom Namibia is hiring an IT Systems Administrator to manage our server infrastructure. "
            "Responsibilities include Linux server administration, network monitoring, Docker deployments, "
            "and maintaining CI/CD pipelines. Requirements: 2+ years Linux experience, knowledge of AWS or Azure, "
            "scripting in Bash or Python. Full-time role with competitive benefits."
        ),
        "job_type": "full-time",
        "salary": "N$18,000 - N$24,000",
        "source_url": "https://www.myjob.com.na/jobs/sysadmin-telecom-003",
        "source_name": "myjob.com.na",
    },
    {
        "title": "Accountant",
        "company": "PwC Namibia",
        "location": "Windhoek",
        "description": (
            "PwC Namibia is looking for a qualified Accountant to join our audit division. "
            "You will handle financial reporting, tax compliance, and client audits. "
            "Requirements: B.Com Accounting degree, ICAN or ACCA qualification preferred. "
            "Strong knowledge of IFRS, Excel, and Sage accounting software. "
            "Excellent report writing and communication skills essential."
        ),
        "job_type": "full-time",
        "salary": "N$22,000 - N$30,000",
        "source_url": "https://www.myjob.com.na/jobs/accountant-pwc-004",
        "source_name": "myjob.com.na",
    },
    {
        "title": "Marketing Officer",
        "company": "MTC Namibia",
        "location": "Windhoek",
        "description": (
            "MTC Namibia seeks a Marketing Officer to drive digital and traditional marketing campaigns. "
            "You will manage social media channels, coordinate public relations activities, and analyse campaign data. "
            "Requirements: degree in Marketing or Communications, 2+ years marketing experience. "
            "Strong skills in content creation, Microsoft Office, and customer service. Fluency in English and Afrikaans preferred."
        ),
        "job_type": "full-time",
        "salary": "N$16,000 - N$20,000",
        "source_url": "https://www.myjob.com.na/jobs/marketing-officer-mtc-005",
        "source_name": "myjob.com.na",
    },
    {
        "title": "Civil Engineer",
        "company": "Roads Authority Namibia",
        "location": "Windhoek",
        "description": (
            "The Roads Authority is seeking a Civil Engineer for road infrastructure projects across Namibia. "
            "You will oversee design, surveying, and project management of road construction. "
            "Requirements: BSc Civil Engineering, registered with ECN, 5+ years experience. "
            "Proficiency in AutoCAD and GIS software required. Valid driving licence essential. "
            "Permanent full-time position."
        ),
        "job_type": "full-time",
        "salary": "N$35,000 - N$50,000",
        "source_url": "https://www.myjob.com.na/jobs/civil-engineer-ra-006",
        "source_name": "myjob.com.na",
    },
    {
        "title": "Junior Python Developer (Internship)",
        "company": "Trustco Group",
        "location": "Windhoek",
        "description": (
            "Trustco Group offers a 6-month internship for a Junior Python Developer. "
            "You will assist in building internal tools using Python and Django, writing REST APIs, "
            "and working with PostgreSQL databases. Requirements: currently studying Computer Science or "
            "Software Engineering, basic knowledge of Python and Git. Great opportunity to gain real-world experience."
        ),
        "job_type": "internship",
        "salary": "N$5,000",
        "source_url": "https://www.myjob.com.na/jobs/junior-python-intern-trustco-007",
        "source_name": "myjob.com.na",
    },
    {
        "title": "Network Engineer",
        "company": "Paratus Namibia",
        "location": "Windhoek",
        "description": (
            "Paratus Namibia is hiring a Network Engineer to maintain and expand our fibre and wireless network. "
            "Responsibilities: configure and troubleshoot routers, switches, and firewalls; "
            "monitor network performance; implement security protocols. "
            "Requirements: CCNA or CCNP certification, 3+ years experience, Linux and Bash scripting skills. "
            "Contract position, 12 months with possibility of extension."
        ),
        "job_type": "contract",
        "salary": "N$28,000 - N$38,000",
        "source_url": "https://www.myjob.com.na/jobs/network-engineer-paratus-008",
        "source_name": "myjob.com.na",
    },
    {
        "title": "Human Resources Officer",
        "company": "Namibia Power Corporation (NamPower)",
        "location": "Windhoek",
        "description": (
            "NamPower seeks an HR Officer to support recruitment, payroll, and employee relations. "
            "You will manage HR records, coordinate training programmes, and ensure compliance with Namibian labour law. "
            "Requirements: degree in HR Management, 3+ years HR experience, knowledge of Sage HR and payroll systems. "
            "Strong communication, leadership, and problem solving skills. Full-time permanent role."
        ),
        "job_type": "full-time",
        "salary": "N$18,000 - N$24,000",
        "source_url": "https://www.myjob.com.na/jobs/hr-officer-nampower-009",
        "source_name": "myjob.com.na",
    },
    {
        "title": "Backend Developer",
        "company": "FNB Namibia",
        "location": "Windhoek",
        "description": (
            "FNB Namibia is looking for a Backend Developer to join our digital banking team. "
            "You will build and maintain microservices using Python and FastAPI, design PostgreSQL schemas, "
            "and integrate with third-party financial APIs. Requirements: 3+ years Python experience, "
            "REST API development, Docker, Git, and agile/scrum methodology. "
            "Experience with AWS or Azure is advantageous. Full-time position in Windhoek."
        ),
        "job_type": "full-time",
        "salary": "N$30,000 - N$42,000",
        "source_url": "https://www.myjob.com.na/jobs/backend-developer-fnb-010",
        "source_name": "myjob.com.na",
    },
    {
        "title": "Geologist",
        "company": "Dundee Precious Metals Tsumeb",
        "location": "Tsumeb",
        "description": (
            "Dundee Precious Metals is seeking an experienced Geologist for our copper smelting operations in Tsumeb. "
            "You will conduct geological surveys, analyse mineral samples, and use GIS software for mapping. "
            "Requirements: BSc Geology, 3+ years mining experience, valid driving licence. "
            "Knowledge of health and safety regulations essential. Accommodation provided on site."
        ),
        "job_type": "full-time",
        "salary": "N$32,000 - N$45,000",
        "source_url": "https://www.myjob.com.na/jobs/geologist-dundee-tsumeb-011",
        "source_name": "myjob.com.na",
    },
    {
        "title": "Frontend Developer (Part-Time)",
        "company": "Digital Namibia Solutions",
        "location": "Windhoek",
        "description": (
            "Digital Namibia Solutions needs a part-time Frontend Developer to build responsive web applications. "
            "You will work with React, TypeScript, HTML, and CSS to deliver client projects. "
            "Requirements: 2+ years React experience, strong JavaScript and CSS skills, experience with REST APIs. "
            "Remote-friendly, flexible hours. Part-time 20 hours per week."
        ),
        "job_type": "part-time",
        "salary": "N$10,000 - N$14,000",
        "source_url": "https://www.myjob.com.na/jobs/frontend-dev-dns-012",
        "source_name": "myjob.com.na",
    },
]


def seed():
    db = SessionLocal()
    saved = 0
    skipped = 0
    try:
        for data in MOCK_JOBS:
            job = Job(
                title=data["title"],
                company=data["company"],
                location=data.get("location"),
                description=data.get("description"),
                job_type=data.get("job_type"),
                salary=data.get("salary"),
                source_url=data["source_url"],
                source_name=data["source_name"],
                date_scraped=datetime.utcnow(),
            )
            db.add(job)
            try:
                db.commit()
                saved += 1
                print(f"  + {data['title']} @ {data['company']}")
            except IntegrityError:
                db.rollback()
                skipped += 1
    finally:
        db.close()

    print(f"\nDone. {saved} inserted, {skipped} skipped (duplicates).")


if __name__ == "__main__":
    seed()
