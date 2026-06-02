"""
Generates and inserts 300 realistic Namibian job listings into the jobs table.
Safe to run multiple times — skips duplicates via source_url unique constraint.
"""
import re
import sys
import json
import random
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from database.database import SessionLocal
from database.models import Job
from sqlalchemy.exc import IntegrityError

random.seed(42)

TODAY = datetime(2026, 6, 2)

COMPANIES = [
    "MTC Namibia", "NamPower", "Bank of Windhoek", "FNB Namibia", "Nedbank Namibia",
    "Bank of Namibia", "Standard Bank Namibia", "O&L Group", "Namib Mills", "Namdeb",
    "Namport", "Gondwana Collection", "Telecom Namibia", "Paratus Namibia",
    "City of Windhoek", "NUST", "UNAM", "NamWater", "TransNamib",
    "Namibia Breweries", "Shoprite Namibia", "Checkers Namibia", "Pick n Pay Namibia",
    "Woermann Brock", "Pupkewitz Group", "Bidvest Namibia", "Mannheimer Insurance",
    "Old Mutual Namibia", "Sanlam Namibia", "Momentum Namibia", "Agra Namibia",
    "FarmBiz Namibia", "Swakop Uranium", "Husab Mine", "Rossing Uranium",
    "Debmarine Namibia", "Wilderness Safaris", "Beyond Namibia", "NHE Namibia",
    "Roads Authority Namibia",
]

LOCATIONS = [
    "Windhoek", "Walvis Bay", "Swakopmund", "Oshakati", "Rundu", "Luderitz",
    "Keetmanshoop", "Grootfontein", "Otjiwarongo", "Mariental", "Gobabis",
    "Tsumeb", "Ondangwa", "Rehoboth", "Katima Mulilo",
]

# Companies with preferred or fixed locations
COMPANY_HOME = {
    "Namdeb":               ["Luderitz", "Windhoek"],
    "Namport":              ["Walvis Bay"],
    "Swakop Uranium":       ["Swakopmund", "Windhoek"],
    "Husab Mine":           ["Swakopmund"],
    "Rossing Uranium":      ["Swakopmund", "Windhoek"],
    "Debmarine Namibia":    ["Walvis Bay", "Windhoek"],
    "City of Windhoek":     ["Windhoek"],
    "NUST":                 ["Windhoek"],
    "UNAM":                 ["Windhoek", "Oshakati"],
    "Bank of Namibia":      ["Windhoek"],
    "Roads Authority Namibia": ["Windhoek", "Walvis Bay", "Oshakati"],
    "NamWater":             ["Windhoek", "Walvis Bay", "Oshakati"],
    "TransNamib":           ["Windhoek", "Walvis Bay"],
    "MTC Namibia":          ["Windhoek", "Oshakati", "Walvis Bay"],
    "NamPower":             ["Windhoek", "Walvis Bay"],
    "Telecom Namibia":      ["Windhoek", "Oshakati", "Walvis Bay"],
    "Gondwana Collection":  ["Windhoek"],
    "Wilderness Safaris":   ["Windhoek"],
    "Beyond Namibia":       ["Windhoek"],
    "NHE Namibia":          ["Windhoek"],
}

# Weighted pool: mostly Full-time
JOB_TYPES_POOL = (
    ["Full-time"] * 12 + ["Part-time"] * 2 + ["Contract"] * 3 + ["Internship"] * 1
)

# (category, title, skills_csv, min_salary_k, max_salary_k)  — salary in thousands NAD/month
TEMPLATES = [
    # ── Technology ──────────────────────────────────────────────────────────────
    ("Technology", "Software Developer",
     "Python, JavaScript, SQL, Git, REST API, Docker", 20, 40),
    ("Technology", "Systems Analyst",
     "SQL, business analysis, requirements gathering, Microsoft Office, project management", 18, 32),
    ("Technology", "IT Support Technician",
     "Windows, Linux, networking, hardware troubleshooting, helpdesk support", 10, 18),
    ("Technology", "Network Engineer",
     "Cisco, CCNA, routing and switching, firewalls, Linux, network monitoring", 25, 45),
    ("Technology", "Cybersecurity Analyst",
     "penetration testing, SIEM, firewall management, security auditing, Linux", 28, 50),
    ("Technology", "Database Administrator",
     "SQL, PostgreSQL, Oracle, backup and recovery, performance tuning", 22, 38),
    ("Technology", "Web Developer",
     "HTML, CSS, JavaScript, React, REST API, PHP", 18, 32),
    ("Technology", "Mobile Developer",
     "React Native, Flutter, Java, Swift, REST API, Git", 22, 38),
    ("Technology", "IT Project Manager",
     "project management, agile, scrum, PMP, MS Project, stakeholder management", 28, 48),
    ("Technology", "Data Analyst",
     "Python, R, Excel, Power BI, SQL, statistics", 18, 34),
    # ── Finance ─────────────────────────────────────────────────────────────────
    ("Finance", "Accountant",
     "IFRS, SAP, Excel, bookkeeping, financial reporting, tax compliance", 18, 32),
    ("Finance", "Financial Analyst",
     "Excel, Power BI, financial modelling, forecasting, SQL", 22, 38),
    ("Finance", "Auditor",
     "IFRS, auditing, risk assessment, Excel, internal controls", 22, 40),
    ("Finance", "Tax Consultant",
     "tax legislation, IFRS, Excel, VAT compliance, accounting", 20, 35),
    ("Finance", "Credit Analyst",
     "credit assessment, Excel, financial analysis, banking, risk management", 18, 30),
    ("Finance", "Treasury Officer",
     "cash management, financial modelling, Excel, banking, forex risk management", 22, 36),
    ("Finance", "Finance Manager",
     "IFRS, SAP, leadership, budgeting, financial reporting, team management", 40, 65),
    ("Finance", "Bookkeeper",
     "Sage, Excel, payroll, accounts payable, accounts receivable", 10, 20),
    ("Finance", "Payroll Administrator",
     "Sage, Excel, payroll processing, labour law, HR systems", 12, 22),
    ("Finance", "Risk Officer",
     "risk management, compliance, Excel, risk reporting, auditing", 25, 42),
    # ── Engineering ─────────────────────────────────────────────────────────────
    ("Engineering", "Civil Engineer",
     "AutoCAD, GIS, project management, structural analysis, driving licence", 30, 55),
    ("Engineering", "Electrical Engineer",
     "AutoCAD, SCADA, electrical systems, commissioning, safety standards", 32, 58),
    ("Engineering", "Mechanical Engineer",
     "AutoCAD, SolidWorks, maintenance planning, reliability engineering", 30, 52),
    ("Engineering", "Mining Engineer",
     "mine planning, blasting certificate, HSE, AutoCAD, mine design", 40, 70),
    ("Engineering", "Process Engineer",
     "chemical engineering, process optimisation, HSE, AutoCAD, P and ID drawings", 28, 50),
    ("Engineering", "Environmental Engineer",
     "EIA, environmental monitoring, GIS, report writing, compliance", 25, 45),
    ("Engineering", "Structural Engineer",
     "AutoCAD, ETABS, STAAD Pro, structural analysis, concrete design", 30, 52),
    ("Engineering", "Project Engineer",
     "AutoCAD, project management, MS Project, quality control, contract management", 28, 48),
    ("Engineering", "Safety Officer",
     "HSE, first aid, safety auditing, incident investigation, driving licence", 18, 32),
    ("Engineering", "Quality Control Inspector",
     "ISO standards, quality management, measurement tools, non-destructive testing", 16, 28),
    # ── Healthcare ──────────────────────────────────────────────────────────────
    ("Healthcare", "Registered Nurse",
     "patient care, clinical assessment, medication management, first aid, HPCNA registration", 16, 28),
    ("Healthcare", "Medical Officer",
     "clinical diagnosis, patient management, report writing, HPCNA registration, emergency care", 35, 60),
    ("Healthcare", "Pharmacist",
     "pharmacy practice, drug dispensing, stock management, HPCNA registration", 28, 45),
    ("Healthcare", "Laboratory Technician",
     "laboratory testing, quality control, equipment calibration, HPCNA registration", 14, 25),
    ("Healthcare", "Radiographer",
     "X-ray, MRI, CT scanning, patient care, HPCNA registration, radiological safety", 18, 32),
    ("Healthcare", "Physiotherapist",
     "rehabilitation, patient assessment, exercise therapy, HPCNA registration", 18, 32),
    ("Healthcare", "Environmental Health Officer",
     "food safety, environmental monitoring, public health, driving licence, HPCNA registration", 14, 24),
    ("Healthcare", "Hospital Administrator",
     "healthcare administration, project management, Microsoft Office, HR management", 22, 38),
    # ── Administration ──────────────────────────────────────────────────────────
    ("Administration", "Administrative Officer",
     "Microsoft Office, filing, communication, report writing, record keeping", 10, 18),
    ("Administration", "Executive Assistant",
     "Microsoft Office, communication, scheduling, report writing, project coordination", 14, 24),
    ("Administration", "Office Manager",
     "Microsoft Office, leadership, office management, communication, budgeting", 18, 30),
    ("Administration", "Records Officer",
     "document management, Microsoft Office, filing, data entry, archiving", 10, 18),
    ("Administration", "Receptionist",
     "Microsoft Office, communication, customer service, telephone skills", 8, 14),
    ("Administration", "Data Entry Clerk",
     "Microsoft Office, typing, data capture, accuracy, time management", 8, 14),
    ("Administration", "Procurement Officer",
     "procurement, supply chain, Microsoft Office, negotiation, contract management", 18, 30),
    ("Administration", "Logistics Coordinator",
     "logistics, supply chain, Microsoft Office, driving licence, planning", 16, 28),
    # ── Sales and Marketing ─────────────────────────────────────────────────────
    ("Sales and Marketing", "Sales Representative",
     "sales, customer service, CRM, communication, driving licence", 10, 22),
    ("Sales and Marketing", "Marketing Officer",
     "marketing, social media, Microsoft Office, content creation, campaign management", 14, 24),
    ("Sales and Marketing", "Brand Manager",
     "brand management, marketing strategy, Microsoft Office, digital marketing, analytics", 28, 45),
    ("Sales and Marketing", "Digital Marketing Specialist",
     "digital marketing, social media, Google Analytics, SEO, content marketing", 16, 28),
    ("Sales and Marketing", "Customer Service Agent",
     "customer service, Microsoft Office, communication, CRM, problem solving", 8, 16),
    ("Sales and Marketing", "Business Development Officer",
     "business development, sales, market research, Microsoft Office, communication", 18, 32),
    ("Sales and Marketing", "Key Accounts Manager",
     "account management, sales, CRM, communication, negotiation", 22, 40),
    # ── Human Resources ─────────────────────────────────────────────────────────
    ("Human Resources", "HR Officer",
     "HR management, recruitment, payroll, labour law, Microsoft Office", 14, 26),
    ("Human Resources", "Recruitment Specialist",
     "recruitment, HR management, LinkedIn, communication, interviewing", 16, 28),
    ("Human Resources", "Training and Development Officer",
     "training design, facilitation, HR management, Microsoft Office, LMS", 14, 26),
    ("Human Resources", "Labour Relations Officer",
     "labour law, HR management, negotiation, dispute resolution, report writing", 18, 32),
    ("Human Resources", "Compensation and Benefits Analyst",
     "compensation analysis, HR management, Excel, payroll, job evaluation", 20, 35),
    # ── Legal ────────────────────────────────────────────────────────────────────
    ("Legal", "Legal Officer",
     "legal research, contract drafting, compliance, report writing, communication", 20, 38),
    ("Legal", "Compliance Officer",
     "compliance management, legal research, report writing, Microsoft Office, risk management", 22, 40),
    ("Legal", "Company Secretary",
     "corporate governance, board secretarial, legal research, Microsoft Office, Companies Act", 25, 45),
    ("Legal", "Contract Administrator",
     "contract management, legal research, Microsoft Office, negotiation, procurement law", 18, 32),
    ("Legal", "Paralegal",
     "legal research, Microsoft Office, communication, document management, court filing", 10, 18),
    # ── Education ────────────────────────────────────────────────────────────────
    ("Education", "Lecturer",
     "teaching, research, academic writing, Microsoft Office, curriculum development", 20, 38),
    ("Education", "Teacher",
     "lesson planning, classroom management, Microsoft Office, communication, assessment", 14, 24),
    ("Education", "Academic Coordinator",
     "academic administration, Microsoft Office, communication, project management", 18, 30),
    ("Education", "Research Officer",
     "research methodology, data analysis, Microsoft Office, report writing, statistics", 18, 32),
    ("Education", "Library Officer",
     "library management, Microsoft Office, cataloguing, information management", 12, 20),
    # ── Hospitality ──────────────────────────────────────────────────────────────
    ("Hospitality", "Lodge Manager",
     "hospitality management, guest relations, budgeting, Microsoft Office, staff management", 22, 40),
    ("Hospitality", "Chef",
     "culinary arts, menu planning, kitchen management, HACCP, food safety", 14, 26),
    ("Hospitality", "Front Office Manager",
     "front desk operations, Microsoft Office, customer service, reservations management, PMS", 16, 28),
    ("Hospitality", "Reservations Agent",
     "reservations management, Microsoft Office, customer service, communication, Tourplan", 10, 16),
    ("Hospitality", "Tour Guide",
     "tourism knowledge, communication, driving licence, first aid, customer service", 10, 18),
    ("Hospitality", "Food and Beverage Manager",
     "F and B management, HACCP, Microsoft Office, cost control, staff management", 18, 32),
]

# Three description variants per category — indexed as seq % 3
DESCRIPTION_TEMPLATES = {
    "Technology": [
        (
            "{company} is seeking a {title} to join our technology team in {location}. "
            "You will design, develop, and maintain systems using {skill1} and {skill2}, "
            "collaborating closely with business stakeholders to deliver reliable digital solutions. "
            "Requirements: BSc in Computer Science or related field, {exp}+ years of relevant experience, "
            "strong problem-solving ability and attention to detail. "
            "{jtype} position. Closing date: {closing}."
        ),
        (
            "{company} has an exciting vacancy for a {title} based in {location}. "
            "The successful applicant will deliver technical solutions, ensure system reliability, "
            "and drive continuous improvement initiatives across the organisation. "
            "Requirements: degree in IT or Engineering, {exp}+ years hands-on experience "
            "with {skill1} and {skill2}, strong communication skills. "
            "{jtype} role with competitive remuneration. Closing date: {closing}."
        ),
        (
            "A great opportunity exists at {company} for a {title} in {location}. "
            "Responsibilities include implementing technical projects, supporting end users, "
            "and documenting processes to ensure long-term maintainability. "
            "Requirements: relevant tertiary qualification, {exp}+ years experience, "
            "proficiency in {skill1} and {skill2}. "
            "Closing date: {closing}."
        ),
    ],
    "Finance": [
        (
            "{company} invites applications for a {title} within our Finance department in {location}. "
            "You will manage financial records, prepare management accounts, and ensure compliance "
            "with IFRS and Namibian financial regulations. "
            "Requirements: B.Com Accounting or Finance, CA(Nam)/ACCA/CIMA preferred, "
            "{exp}+ years relevant experience with {skill1} and {skill2}. "
            "{jtype} position. Closing date: {closing}."
        ),
        (
            "An opportunity exists at {company} for a {title} based in {location}. "
            "The incumbent will provide financial insights, support budgeting cycles, "
            "and liaise with internal and external auditors. "
            "Requirements: degree in Finance or Accounting, {exp}+ years experience, "
            "proficiency in {skill1} and {skill2}. "
            "Closing date: {closing}."
        ),
        (
            "{company} is recruiting a {title} to strengthen our finance function in {location}. "
            "Key duties include financial analysis, variance reporting, and preparing "
            "monthly management accounts for senior leadership. "
            "Requirements: B.Com degree, {exp}+ years finance experience, "
            "strong skills in {skill1} and {skill2}. "
            "{jtype} opportunity. Closing date: {closing}."
        ),
    ],
    "Engineering": [
        (
            "{company} seeks a qualified {title} to join our engineering team in {location}. "
            "You will manage technical projects, ensure compliance with safety standards, "
            "and provide engineering expertise across operations. "
            "Requirements: BSc/B.Tech in a relevant Engineering discipline, registered with ECN, "
            "{exp}+ years experience. Proficiency in {skill1} required. "
            "{jtype} role. Closing date: {closing}."
        ),
        (
            "An exciting engineering opportunity exists at {company} for a {title} in {location}. "
            "Responsibilities include design, commissioning, maintenance, and continuous improvement "
            "of technical systems and infrastructure. "
            "Requirements: relevant engineering degree, {exp}+ years experience, "
            "strong skills in {skill1} and {skill2}, valid driving licence advantageous. "
            "Closing date: {closing}."
        ),
        (
            "{company} is looking for a {title} to support operations in {location}. "
            "The successful candidate will oversee technical teams, prepare engineering reports, "
            "and ensure strict compliance with HSE requirements. "
            "Requirements: BSc Engineering, {exp}+ years in a similar role, "
            "proficiency in {skill1} and project management tools. "
            "{jtype} position. Closing date: {closing}."
        ),
    ],
    "Healthcare": [
        (
            "{company} invites applications for a {title} to serve our patients "
            "and community in {location}. "
            "You will deliver high-quality clinical care, maintain patient records, "
            "and adhere to HPCNA guidelines and professional standards. "
            "Requirements: relevant healthcare qualification, current HPCNA registration, "
            "{exp}+ years clinical experience. "
            "{jtype} position. Closing date: {closing}."
        ),
        (
            "A vacancy exists at {company} for a {title} based in {location}. "
            "Responsibilities include patient assessment, treatment planning, "
            "and collaborating with a multidisciplinary healthcare team to achieve positive outcomes. "
            "Requirements: accredited degree or diploma in the relevant field, "
            "HPCNA registration, {exp}+ years experience. "
            "Closing date: {closing}."
        ),
        (
            "{company} is seeking a dedicated {title} for our health services in {location}. "
            "The candidate will ensure excellent patient outcomes, oversee health and safety standards, "
            "and mentor junior clinical staff. "
            "Requirements: recognised healthcare qualification, HPCNA registration, "
            "{exp}+ years of clinical or health administration experience. "
            "{jtype} role. Closing date: {closing}."
        ),
    ],
    "Administration": [
        (
            "{company} is looking for an organised {title} to support our operations in {location}. "
            "You will manage correspondence, coordinate meetings, maintain records, "
            "and provide general administrative support to the management team. "
            "Requirements: relevant diploma or degree, {exp}+ years administrative experience, "
            "proficiency in {skill1} and {skill2}. "
            "{jtype} position. Closing date: {closing}."
        ),
        (
            "A vacancy for a {title} has arisen at {company} in {location}. "
            "Responsibilities include scheduling, document management, liaising with stakeholders, "
            "and ensuring smooth day-to-day office operations. "
            "Requirements: Diploma in Office Administration or equivalent, "
            "{exp}+ years experience in a similar administrative role, strong Microsoft Office skills. "
            "Closing date: {closing}."
        ),
        (
            "{company} seeks a proactive {title} in {location} to maintain "
            "efficient office and administrative functions. "
            "You will support senior management, prepare reports, coordinate procurement of supplies, "
            "and handle petty cash. "
            "Requirements: relevant qualification, {exp}+ years office experience, "
            "excellent communication and organisational ability. "
            "{jtype} role. Closing date: {closing}."
        ),
    ],
    "Sales and Marketing": [
        (
            "{company} is seeking a results-driven {title} to grow our customer base in {location}. "
            "You will develop and execute sales strategies, build lasting client relationships, "
            "and consistently meet monthly revenue targets. "
            "Requirements: degree in Marketing or Business, {exp}+ years experience, "
            "proficiency in {skill1} and {skill2}. "
            "{jtype} position. Closing date: {closing}."
        ),
        (
            "An opportunity exists at {company} for an ambitious {title} in {location}. "
            "The successful candidate will manage marketing campaigns, analyse consumer data, "
            "and coordinate promotional activities across digital and traditional channels. "
            "Requirements: relevant degree, {exp}+ years marketing or sales experience, "
            "strong analytical and creative mindset. "
            "Closing date: {closing}."
        ),
        (
            "{company} invites applications for a talented {title} in {location}. "
            "Responsibilities include developing customer relationships, "
            "identifying new business opportunities, and reporting on market trends to management. "
            "Requirements: degree or diploma in Sales/Marketing, {exp}+ years industry experience, "
            "strong communication and negotiation skills. "
            "{jtype} role. Closing date: {closing}."
        ),
    ],
    "Human Resources": [
        (
            "{company} is recruiting a {title} to support our people management function in {location}. "
            "You will administer HR processes, coordinate recruitment campaigns, "
            "and ensure compliance with the Namibian Labour Act. "
            "Requirements: degree in HR Management or related field, {exp}+ years HR experience, "
            "knowledge of {skill1} and {skill2}. "
            "{jtype} position. Closing date: {closing}."
        ),
        (
            "A vacancy exists at {company} for a {title} based in {location}. "
            "Responsibilities include employee relations, performance management, "
            "and implementing HR policies aligned with organisational goals. "
            "Requirements: relevant HR qualification, {exp}+ years experience, "
            "strong knowledge of Namibian labour law and HR best practices. "
            "Closing date: {closing}."
        ),
        (
            "{company} seeks an experienced {title} in {location} "
            "to drive our talent and people strategy. "
            "You will lead recruitment drives, manage HR reporting, "
            "and foster a positive and productive workplace culture. "
            "Requirements: degree in HR or Business Administration, {exp}+ years HR experience, "
            "proficiency in HR systems and payroll. "
            "{jtype} role. Closing date: {closing}."
        ),
    ],
    "Legal": [
        (
            "{company} invites applications for a {title} "
            "in our Legal and Compliance division in {location}. "
            "You will provide legal advice, draft and review contracts, "
            "and ensure corporate governance standards are maintained at all levels. "
            "Requirements: LLB degree, admitted to the High Court of Namibia, "
            "{exp}+ years post-admission experience. "
            "{jtype} position. Closing date: {closing}."
        ),
        (
            "A vacancy exists at {company} for a {title} based in {location}. "
            "Responsibilities include legal research, managing regulatory submissions, "
            "and supporting internal compliance and risk management programmes. "
            "Requirements: LLB or related legal qualification, "
            "{exp}+ years experience in {skill1} and {skill2}. "
            "Closing date: {closing}."
        ),
        (
            "{company} seeks a meticulous {title} in {location} "
            "to strengthen our legal and governance function. "
            "You will assist with litigation support, contract administration, "
            "and ensuring the organisation meets all statutory obligations. "
            "Requirements: LLB or Diploma in Law, {exp}+ years experience, "
            "strong research and analytical ability. "
            "{jtype} role. Closing date: {closing}."
        ),
    ],
    "Education": [
        (
            "{company} invites qualified applicants for the position of {title} in {location}. "
            "You will deliver quality instruction, assess student progress, "
            "and contribute to departmental research and development activities. "
            "Requirements: relevant academic qualification (Master's or higher for lecturing), "
            "{exp}+ years teaching or research experience. "
            "{jtype} position. Closing date: {closing}."
        ),
        (
            "A vacancy for a {title} exists at {company} in {location}. "
            "Responsibilities include curriculum delivery, student mentoring, "
            "and participating in community engagement and outreach projects. "
            "Requirements: degree in the relevant field, teaching qualification where applicable, "
            "{exp}+ years experience in education or research. "
            "Closing date: {closing}."
        ),
        (
            "{company} seeks a dedicated {title} to join our academic team in {location}. "
            "The appointee will design learning materials, facilitate workshops, "
            "and contribute to institutional quality assurance and accreditation processes. "
            "Requirements: relevant degree, {exp}+ years experience, "
            "strong communication and facilitation skills. "
            "{jtype} role. Closing date: {closing}."
        ),
    ],
    "Hospitality": [
        (
            "{company} is seeking an experienced {title} "
            "to deliver world-class guest experiences in {location}. "
            "You will manage hospitality operations, lead a diverse team, "
            "and uphold the brand's high standards of service and presentation. "
            "Requirements: hospitality management qualification, {exp}+ years in a similar role, "
            "excellent interpersonal and leadership skills. "
            "{jtype} position. Closing date: {closing}."
        ),
        (
            "An exciting opportunity exists at {company} for a {title} in {location}. "
            "Responsibilities include overseeing daily operations, managing budgets, "
            "ensuring guest satisfaction, and mentoring front-line hospitality staff. "
            "Requirements: diploma or degree in Hospitality Management, "
            "{exp}+ years experience in a luxury tourism or hotel environment. "
            "Closing date: {closing}."
        ),
        (
            "{company} invites applications for a {title} based in {location}. "
            "The successful candidate will uphold service excellence, coordinate logistics, "
            "and contribute to a memorable and authentic guest journey. "
            "Requirements: relevant hospitality qualification, "
            "{exp}+ years hands-on experience, passion for Namibian tourism and culture. "
            "{jtype} role. Closing date: {closing}."
        ),
    ],
}


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def _pick_location(company: str) -> str:
    if company in COMPANY_HOME:
        return random.choice(COMPANY_HOME[company])
    # Windhoek most likely (weight 4), others weight 1
    weights = [4] + [1] * (len(LOCATIONS) - 1)
    return random.choices(LOCATIONS, weights=weights, k=1)[0]


def _pick_exp(min_k: int) -> int:
    if min_k >= 40:
        return random.randint(5, 8)
    if min_k >= 25:
        return random.randint(3, 6)
    if min_k >= 15:
        return random.randint(2, 4)
    return random.randint(1, 3)


def _pick_salary(min_k: int, max_k: int, include: bool) -> str | None:
    if not include:
        return None
    mid = (min_k + max_k) // 2
    lo = random.randint(min_k, mid)
    spread = random.choice([5, 8, 10, 12, 15])
    hi = min(lo + spread, max_k)
    if hi <= lo:
        hi = lo + 5
    return f"N${lo:,},000 - N${hi:,},000 per month"


def generate_jobs() -> list[dict]:
    # Build 300 unique (template_idx, company_idx) pairs
    all_combos = [
        (t, c)
        for t in range(len(TEMPLATES))
        for c in range(len(COMPANIES))
    ]
    random.shuffle(all_combos)
    selected = all_combos[:300]

    # Determine which ~40 % get a salary
    salary_flags = [True] * 120 + [False] * 180
    random.shuffle(salary_flags)

    jobs: list[dict] = []
    for seq, ((t_idx, c_idx), has_salary) in enumerate(zip(selected, salary_flags), start=1):
        category, title, skills_csv, min_k, max_k = TEMPLATES[t_idx]
        company  = COMPANIES[c_idx]
        location = _pick_location(company)
        job_type = random.choice(JOB_TYPES_POOL)
        exp      = _pick_exp(min_k)

        closing_days = random.randint(7, 60)
        closing = TODAY + timedelta(days=closing_days)
        closing_str = f"{closing.day} {closing.strftime('%B %Y')}"

        salary = _pick_salary(min_k, max_k, has_salary)

        slug = _slug(f"{title} {company}")
        source_url = f"https://seed.namibjobs.na/jobs/{slug}-{seq:04d}"

        # Pick description variant
        skill_parts = [s.strip() for s in skills_csv.split(",")]
        skill1 = skill_parts[0] if len(skill_parts) > 0 else "relevant tools"
        skill2 = skill_parts[1] if len(skill_parts) > 1 else "industry software"

        desc_tmpl = DESCRIPTION_TEMPLATES[category][seq % 3]
        description = desc_tmpl.format(
            company=company,
            title=title,
            location=location,
            skill1=skill1,
            skill2=skill2,
            exp=exp,
            jtype=job_type,
            closing=closing_str,
        )

        jobs.append({
            "title":       title,
            "company":     company,
            "location":    location,
            "description": description,
            "skills":      skills_csv,
            "salary":      salary,
            "job_type":    job_type,
            "source_url":  source_url,
            "source_name": "NamibJobs Seed",
        })

    return jobs


def seed() -> None:
    db = SessionLocal()
    saved = skipped = 0
    try:
        for data in generate_jobs():
            job = Job(
                title=data["title"],
                company=data["company"],
                location=data["location"],
                description=data["description"],
                skills=data["skills"],
                salary=data["salary"],
                job_type=data["job_type"],
                source_url=data["source_url"],
                source_name=data["source_name"],
                date_scraped=datetime.utcnow(),
            )
            db.add(job)
            try:
                db.commit()
                saved += 1
                print(f"  [{saved:>3}] {data['title']} @ {data['company']} ({data['location']})")
            except IntegrityError:
                db.rollback()
                skipped += 1
    finally:
        db.close()

    print(f"\nDone. {saved} inserted, {skipped} skipped (duplicates).")


if __name__ == "__main__":
    seed()
