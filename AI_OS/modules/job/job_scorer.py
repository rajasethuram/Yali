"""
Job Scorer — scores job match against user resume using NLP similarity.
Compares JD skills vs resume skills, experience level, location.
"""
import re
import sys
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from modules.cognitive.resume_parser import load_profile

SKILL_KEYWORDS = [
    "python", "java", "javascript", "typescript", "c++", "c#", "go", "rust",
    "kotlin", "swift", "ruby", "php", "scala", "r", "bash", "sql",
    "react", "angular", "vue", "django", "flask", "fastapi", "spring", "express",
    "nextjs", "nestjs", "tensorflow", "pytorch", "keras", "sklearn", "pandas", "numpy",
    "aws", "azure", "gcp", "docker", "kubernetes", "terraform", "jenkins",
    "mysql", "postgresql", "mongodb", "redis", "elasticsearch", "cassandra",
    "machine learning", "deep learning", "nlp", "computer vision", "llm", "rag",
    "rest api", "graphql", "microservices", "agile", "scrum", "git",
    "spark", "hadoop", "kafka", "airflow", "node.js", "nodejs",
]

EXP_PATTERNS = [
    (r"(\d+)\+?\s*years?", lambda m: int(m.group(1))),
    (r"(\d+)\s*-\s*(\d+)\s*years?", lambda m: (int(m.group(1)) + int(m.group(2))) // 2),
]

LEVEL_KEYWORDS = {
    "fresher": 0, "entry": 1, "junior": 1, "associate": 1,
    "mid": 3, "intermediate": 3, "senior": 5, "lead": 7,
    "principal": 8, "staff": 8, "architect": 9, "manager": 7,
}


def extract_jd_skills(jd_text: str) -> set[str]:
    text_lower = jd_text.lower()
    found = set()
    for skill in SKILL_KEYWORDS:
        if re.search(r'\b' + re.escape(skill) + r'\b', text_lower):
            found.add(skill)
    return found


def extract_jd_required_experience(jd_text: str) -> int:
    text_lower = jd_text.lower()
    for pattern, extractor in EXP_PATTERNS:
        m = re.search(pattern, text_lower)
        if m:
            try:
                return extractor(m)
            except Exception:
                pass
    for level, yrs in LEVEL_KEYWORDS.items():
        if level in text_lower:
            return yrs
    return 0


def score_job(jd_text: str, job_title: str = "", job_location: str = "",
              user_profile: Optional[dict] = None) -> dict:
    """
    Returns score dict:
    {
      total: 0-100,
      skill_match: 0-100,
      experience_match: 0-100,
      location_match: 0-100,
      matched_skills: [...],
      missing_skills: [...],
      required_exp: int,
      user_exp: int,
    }
    """
    profile = user_profile or load_profile()
    if not profile:
        return {"total": 50, "skill_match": 50, "experience_match": 50,
                "location_match": 50, "matched_skills": [], "missing_skills": [],
                "required_exp": 0, "user_exp": 0}

    user_skills = set(s.lower() for s in profile.get("skills", []))
    user_exp = profile.get("years_experience", 0)

    jd_skills = extract_jd_skills(jd_text)
    required_exp = extract_jd_required_experience(jd_text)

    # Skill match score
    if jd_skills:
        matched = user_skills & jd_skills
        skill_match = round(len(matched) / len(jd_skills) * 100)
        missing = jd_skills - user_skills
    else:
        matched = set()
        skill_match = 60  # no skills listed = neutral
        missing = set()

    # Experience match score
    if required_exp == 0:
        exp_match = 80
    elif user_exp == 0:
        exp_match = 50
    else:
        diff = abs(user_exp - required_exp)
        if diff == 0:
            exp_match = 100
        elif diff <= 1:
            exp_match = 85
        elif diff <= 2:
            exp_match = 70
        elif user_exp > required_exp:
            # Overqualified is ok
            exp_match = max(60, 100 - diff * 8)
        else:
            # Underqualified — penalize more
            exp_match = max(20, 100 - diff * 15)

    # Location match score
    user_locations = []
    for comp in profile.get("companies", []):
        pass  # No direct location in profile

    loc_lower = job_location.lower()
    loc_match = 70  # default neutral
    preferred_locations = ["bangalore", "bengaluru", "hyderabad", "pune", "chennai",
                           "mumbai", "delhi", "remote", "work from home", "wfh"]
    if any(p in loc_lower for p in preferred_locations):
        loc_match = 100
    elif "india" in loc_lower or loc_lower == "":
        loc_match = 80

    # Semantic boost via sentence-transformers (if available)
    semantic_boost = 0
    try:
        from sentence_transformers import SentenceTransformer, util
        model = _get_st_model()
        if model and jd_text and profile.get("raw_text_preview"):
            jd_emb = model.encode(jd_text[:512], convert_to_tensor=True)
            resume_emb = model.encode(profile["raw_text_preview"][:512], convert_to_tensor=True)
            sim = float(util.pytorch_cos_sim(jd_emb, resume_emb)[0][0])
            semantic_boost = int(sim * 20)  # up to +20 points
    except Exception:
        pass

    # Weighted total
    total = round(
        skill_match * 0.45 +
        exp_match * 0.30 +
        loc_match * 0.15 +
        semantic_boost * 0.10
    )
    total = min(100, total)

    return {
        "total": total,
        "skill_match": skill_match,
        "experience_match": exp_match,
        "location_match": loc_match,
        "semantic_boost": semantic_boost,
        "matched_skills": sorted(matched),
        "missing_skills": sorted(missing),
        "required_exp": required_exp,
        "user_exp": user_exp,
    }


_st_model = None

def _get_st_model():
    global _st_model
    if _st_model is None:
        try:
            from sentence_transformers import SentenceTransformer
            _st_model = SentenceTransformer("all-MiniLM-L6-v2")
        except Exception:
            pass
    return _st_model


def score_jobs_batch(jobs: list, min_score: int = 65,
                     user_profile: Optional[dict] = None) -> list:
    """Score a list of job dicts/Job objects, filter by min_score, sort desc."""
    profile = user_profile or load_profile()
    scored = []

    for job in jobs:
        if hasattr(job, 'to_dict'):
            job_dict = job.to_dict()
        else:
            job_dict = dict(job)

        result = score_job(
            jd_text=job_dict.get("jd_text", ""),
            job_title=job_dict.get("title", ""),
            job_location=job_dict.get("location", ""),
            user_profile=profile,
        )
        job_dict["match_score"] = result["total"]
        job_dict["score_details"] = result
        scored.append(job_dict)

    # Filter and sort
    filtered = [j for j in scored if j["match_score"] >= min_score]
    filtered.sort(key=lambda x: x["match_score"], reverse=True)

    print(f"[Scorer] {len(jobs)} jobs scored — {len(filtered)} passed >{min_score}% threshold")
    return filtered


if __name__ == "__main__":
    sample_jd = """
    We are looking for a Senior Python Developer with 4+ years experience.
    Required skills: Python, Django, FastAPI, PostgreSQL, Docker, AWS, REST API.
    Nice to have: Kubernetes, Redis, CI/CD, microservices.
    Location: Bangalore (Remote friendly)
    """
    result = score_job(sample_jd, job_location="Bangalore")
    print("=== Job Score Result ===")
    print(f"Total: {result['total']}/100")
    print(f"Skill match: {result['skill_match']}%")
    print(f"Exp match: {result['experience_match']}%")
    print(f"Matched skills: {result['matched_skills']}")
    print(f"Missing skills: {result['missing_skills']}")
