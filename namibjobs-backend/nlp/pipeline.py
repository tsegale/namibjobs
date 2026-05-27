import re
import json
import spacy
from sentence_transformers import SentenceTransformer

nlp = spacy.load("en_core_web_sm")
embedder = SentenceTransformer("all-MiniLM-L6-v2")

# ---------------------------------------------------------------------------
# Skills dictionary — extend as needed
# ---------------------------------------------------------------------------
SKILLS = {
    # Programming languages
    "python", "java", "javascript", "typescript", "c++", "c#", "php", "ruby",
    "swift", "kotlin", "r", "matlab", "scala", "go", "rust", "bash", "sql",
    # Web / frameworks
    "react", "angular", "vue", "node.js", "django", "flask", "fastapi",
    "spring", "laravel", "express", "html", "css", "rest api", "graphql",
    # Data / ML
    "pandas", "numpy", "scikit-learn", "tensorflow", "pytorch", "keras",
    "machine learning", "deep learning", "data analysis", "data science",
    "power bi", "tableau", "excel", "spss", "stata",
    # Databases
    "postgresql", "mysql", "sqlite", "mongodb", "redis", "oracle", "mssql",
    # Cloud / DevOps
    "aws", "azure", "gcp", "docker", "kubernetes", "linux", "git", "ci/cd",
    "terraform", "jenkins",
    # Office / business
    "microsoft office", "word", "outlook", "sharepoint", "sap", "quickbooks",
    "sage", "pastel", "xero",
    # Finance / accounting
    "accounting", "bookkeeping", "auditing", "ifrs", "gaap", "tax",
    "payroll", "budgeting", "financial reporting", "cost accounting",
    # General professional
    "project management", "agile", "scrum", "communication", "leadership",
    "teamwork", "problem solving", "research", "report writing",
    "customer service", "sales", "marketing", "public relations",
    # Namibia-relevant
    "afrikaans", "german", "oshiwambo", "mining", "geology", "gis",
    "surveying", "procurement", "logistics", "supply chain", "hse",
    "health and safety", "first aid", "driving licence",
}

JOB_TYPE_MAP = {
    "full-time": [r"full[\s\-]?time", r"\bpermanent\b"],
    "part-time": [r"part[\s\-]?time"],
    "contract": [r"\bcontract\b", r"\bfixed[\s\-]?term\b", r"\btemporary\b", r"\btemp\b"],
    "internship": [r"\bintern(ship)?\b", r"\bgraduate trainee\b", r"\blearnership\b"],
    "freelance": [r"\bfreelance\b", r"\bconsultant\b", r"\bself[\s\-]?employed\b"],
}


def extract_skills(text: str) -> list[str]:
    lower = text.lower()
    found = []
    for skill in SKILLS:
        pattern = r"\b" + re.escape(skill) + r"\b"
        if re.search(pattern, lower):
            found.append(skill)
    return sorted(found)


def extract_location(text: str) -> str | None:
    doc = nlp(text)
    locations = [
        ent.text.strip()
        for ent in doc.ents
        if ent.label_ in ("GPE", "LOC")
    ]
    if not locations:
        return None
    # Return the most-mentioned location
    return max(set(locations), key=locations.count)


def extract_job_type(text: str) -> str | None:
    lower = text.lower()
    for job_type, patterns in JOB_TYPE_MAP.items():
        for pattern in patterns:
            if re.search(pattern, lower):
                return job_type
    return None


def generate_embedding(text: str) -> list[float]:
    vector = embedder.encode(text, normalize_embeddings=True)
    return vector.tolist()


def process_description(description: str) -> dict:
    """
    Run the full pipeline on a single job description.
    Returns a dict with skills, location, job_type, and embedding.
    """
    if not description:
        return {"skills": [], "location": None, "job_type": None, "embedding": None}

    return {
        "skills": extract_skills(description),
        "location": extract_location(description),
        "job_type": extract_job_type(description),
        "embedding": generate_embedding(description),
    }
