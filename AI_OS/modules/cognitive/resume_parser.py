"""
Resume parser — extracts structured profile from PDF.
Stores to memory/user_profile.json for LLM context injection.
"""
import json
import re
import sys
from pathlib import Path

import spacy
import PyPDF2

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from config.settings import MEMORY_DIR, RESUME_PATH, USER_PROFILE_PATH, USER_NAME

nlp = spacy.load("en_core_web_sm")

SKILL_KEYWORDS = [
    # Languages
    "python", "java", "javascript", "typescript", "c++", "c#", "go", "rust",
    "kotlin", "swift", "ruby", "php", "scala", "r", "matlab", "bash",
    # Frameworks
    "react", "angular", "vue", "django", "flask", "fastapi", "spring", "express",
    "nextjs", "nestjs", "laravel", "rails", "tensorflow", "pytorch", "keras",
    "sklearn", "scikit-learn", "pandas", "numpy",
    # Cloud & DevOps
    "aws", "azure", "gcp", "docker", "kubernetes", "terraform", "ansible",
    "jenkins", "github actions", "ci/cd", "linux", "nginx",
    # Databases
    "mysql", "postgresql", "mongodb", "redis", "elasticsearch", "cassandra",
    "dynamodb", "sqlite", "oracle",
    # AI/ML
    "machine learning", "deep learning", "nlp", "computer vision", "llm",
    "transformers", "bert", "gpt", "fine-tuning", "rag", "langchain",
    # Other
    "rest api", "graphql", "microservices", "agile", "scrum", "git",
    "spark", "hadoop", "kafka", "airflow", "dbt",
]

FILLER_STOP = {"the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for"}


def extract_text_from_pdf(pdf_path: Path) -> str:
    text = ""
    with open(pdf_path, "rb") as f:
        reader = PyPDF2.PdfReader(f)
        for page in reader.pages:
            text += page.extract_text() or ""
    return text


def extract_email(text: str) -> str:
    match = re.search(r"[\w.+-]+@[\w-]+\.[a-zA-Z]{2,}", text)
    return match.group(0) if match else ""


def extract_phone(text: str) -> str:
    match = re.search(r"(\+?\d[\d\s\-().]{7,14}\d)", text)
    return match.group(0).strip() if match else ""


def extract_linkedin(text: str) -> str:
    match = re.search(r"linkedin\.com/in/[\w-]+", text, re.IGNORECASE)
    return match.group(0) if match else ""


def extract_skills(text: str) -> list[str]:
    text_lower = text.lower()
    found = []
    for skill in SKILL_KEYWORDS:
        if skill in text_lower:
            found.append(skill)
    return list(set(found))


def extract_years_experience(text: str) -> int:
    patterns = [
        r"(\d+)\+?\s*years?\s*of\s*(experience|exp)",
        r"(\d+)\+?\s*years?\s*in",
        r"experience\s*of\s*(\d+)\+?\s*years?",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return int(match.group(1))
    return 0


def extract_companies(text: str) -> list[str]:
    doc = nlp(text)
    companies = []
    for ent in doc.ents:
        if ent.label_ == "ORG":
            name = ent.text.strip()
            if len(name) > 2 and name.lower() not in FILLER_STOP:
                companies.append(name)
    seen = set()
    unique = []
    for c in companies:
        if c.lower() not in seen:
            seen.add(c.lower())
            unique.append(c)
    return unique[:10]


def extract_education(text: str) -> list[str]:
    edu_keywords = ["b.tech", "b.e.", "m.tech", "mba", "bsc", "msc", "phd",
                    "bachelor", "master", "degree", "university", "college", "institute"]
    lines = text.split("\n")
    edu_lines = []
    for line in lines:
        if any(k in line.lower() for k in edu_keywords):
            cleaned = line.strip()
            if cleaned and len(cleaned) > 5:
                edu_lines.append(cleaned)
    return edu_lines[:5]


def extract_name(text: str, default_name: str) -> str:
    lines = [l.strip() for l in text.split("\n") if l.strip()]
    for line in lines[:5]:
        doc = nlp(line)
        for ent in doc.ents:
            if ent.label_ == "PERSON":
                return ent.text.strip()
    return default_name


def extract_summary_lines(text: str) -> str:
    summary_markers = ["summary", "profile", "about me", "objective", "overview"]
    lines = text.split("\n")
    capturing = False
    summary_lines = []
    for line in lines:
        stripped = line.strip()
        if any(m in stripped.lower() for m in summary_markers):
            capturing = True
            continue
        if capturing:
            if stripped and not any(
                h in stripped.lower()
                for h in ["experience", "education", "skills", "projects", "certifications"]
            ):
                summary_lines.append(stripped)
            else:
                break
    return " ".join(summary_lines[:3])


def parse_resume(pdf_path: Path = None) -> dict:
    pdf_path = pdf_path or RESUME_PATH
    if not pdf_path.exists():
        print(f"[ResumeParser] No resume found at {pdf_path}")
        return {}

    print(f"[ResumeParser] Parsing {pdf_path.name}...")
    text = extract_text_from_pdf(pdf_path)

    profile = {
        "name": extract_name(text, USER_NAME),
        "email": extract_email(text),
        "phone": extract_phone(text),
        "linkedin": extract_linkedin(text),
        "skills": extract_skills(text),
        "years_experience": extract_years_experience(text),
        "companies": extract_companies(text),
        "education": extract_education(text),
        "summary": extract_summary_lines(text),
        "raw_text_preview": text[:1500],
    }

    MEMORY_DIR.mkdir(parents=True, exist_ok=True)
    with open(USER_PROFILE_PATH, "w") as f:
        json.dump(profile, f, indent=2)

    print(f"[ResumeParser] Profile saved → {USER_PROFILE_PATH}")
    print(f"  Name: {profile['name']}")
    print(f"  Skills ({len(profile['skills'])}): {', '.join(profile['skills'][:10])}")
    print(f"  Companies: {', '.join(profile['companies'][:5])}")
    print(f"  Experience: {profile['years_experience']} years")
    return profile


def load_profile() -> dict:
    if USER_PROFILE_PATH.exists():
        with open(USER_PROFILE_PATH) as f:
            return json.load(f)
    return {}


def get_profile_context_string() -> str:
    profile = load_profile()
    if not profile:
        return "No resume loaded. Answer based on general best practices."

    skills_str = ", ".join(profile.get("skills", [])[:20])
    companies_str = ", ".join(profile.get("companies", [])[:5])
    edu_str = " | ".join(profile.get("education", [])[:2])

    return f"""USER PROFILE:
Name: {profile.get('name', 'The candidate')}
Years of experience: {profile.get('years_experience', 'unknown')}
Skills: {skills_str}
Companies worked at: {companies_str}
Education: {edu_str}
Summary: {profile.get('summary', '')}"""


if __name__ == "__main__":
    import sys
    pdf = Path(sys.argv[1]) if len(sys.argv) > 1 else None
    profile = parse_resume(pdf)
    if profile:
        print("\n--- Profile Context String (used in LLM prompts) ---")
        print(get_profile_context_string())
