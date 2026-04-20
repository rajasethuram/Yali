"""
Resume Tailorer + Cover Letter Generator.
Uses Claude API to rewrite resume summary/skills to match JD keywords (ATS optimization).
Generates tailored cover letter per job.
Outputs PDF files per company.
"""
import json
import sys
import time
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from config.settings import ANTHROPIC_API_KEY, CLAUDE_MIND_MODEL, MEMORY_DIR
from modules.cognitive.resume_parser import load_profile, get_profile_context_string

TAILORED_DIR = MEMORY_DIR / "tailored_resumes"
COVER_LETTER_DIR = MEMORY_DIR / "cover_letters"


def tailor_resume_text(jd_text: str, company: str, role: str) -> dict:
    """
    Returns dict with:
      summary: tailored summary paragraph
      skills_to_highlight: list of skills to emphasize
      cover_letter: 3-paragraph cover letter
      ats_keywords: keywords to include for ATS
    """
    if not ANTHROPIC_API_KEY:
        return {
            "summary": "Add ANTHROPIC_API_KEY to .env to enable tailoring.",
            "skills_to_highlight": [],
            "cover_letter": "Add API key to generate cover letter.",
            "ats_keywords": [],
        }

    import anthropic
    profile = load_profile()
    profile_ctx = get_profile_context_string()

    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    # Resume tailoring
    tailor_prompt = f"""You are an expert resume writer and ATS optimization specialist.

{profile_ctx}

JOB DESCRIPTION:
{jd_text[:2000]}

COMPANY: {company}
ROLE: {role}

Your task:
1. Write a tailored PROFESSIONAL SUMMARY (3-4 sentences) that incorporates exact keywords from the JD and maps the candidate's experience to what the company needs.
2. List the TOP 10 SKILLS to highlight (from resume that match JD requirements).
3. List 8 ATS KEYWORDS from the JD that must appear in the resume.

Respond in this exact JSON format:
{{
  "summary": "...",
  "skills_to_highlight": ["skill1", "skill2", ...],
  "ats_keywords": ["kw1", "kw2", ...]
}}"""

    try:
        response = client.messages.create(
            model=CLAUDE_MIND_MODEL,
            max_tokens=600,
            messages=[{"role": "user", "content": tailor_prompt}]
        )
        raw = response.content[0].text.strip()
        # Extract JSON from response
        start = raw.find('{')
        end = raw.rfind('}') + 1
        if start >= 0 and end > start:
            result = json.loads(raw[start:end])
        else:
            result = {"summary": raw, "skills_to_highlight": [], "ats_keywords": []}
    except Exception as e:
        result = {"summary": f"Error: {e}", "skills_to_highlight": [], "ats_keywords": []}

    # Cover letter generation
    cover_prompt = f"""Write a professional cover letter for this job application.

CANDIDATE PROFILE:
{profile_ctx}

APPLYING TO: {role} at {company}

JOB DESCRIPTION (first 1000 chars):
{jd_text[:1000]}

Write exactly 3 paragraphs:
1. Opening: Who you are + why THIS company specifically excites you (mention their product/mission)
2. Body: Your 2-3 most relevant achievements that directly match what they need (use numbers)
3. Closing: Clear call to action + enthusiasm

Rules:
- No generic phrases like "I am writing to apply"
- Start strong: "After 4 years building..."
- Each paragraph max 4 sentences
- Total: under 250 words
- Professional but human tone"""

    try:
        cover_response = client.messages.create(
            model=CLAUDE_MIND_MODEL,
            max_tokens=500,
            messages=[{"role": "user", "content": cover_prompt}]
        )
        cover_letter = cover_response.content[0].text.strip()
    except Exception as e:
        cover_letter = f"Error generating cover letter: {e}"

    result["cover_letter"] = cover_letter
    return result


def save_cover_letter_txt(cover_letter: str, company: str, role: str) -> Path:
    """Save cover letter as text file."""
    COVER_LETTER_DIR.mkdir(parents=True, exist_ok=True)
    safe_company = re.sub(r'[^\w]', '_', company)[:30]
    fname = COVER_LETTER_DIR / f"cover_{safe_company}_{int(time.time())}.txt"
    with open(fname, "w", encoding="utf-8") as f:
        f.write(f"Cover Letter — {role} at {company}\n")
        f.write("=" * 60 + "\n\n")
        f.write(cover_letter)
    print(f"[Tailorer] Cover letter saved: {fname}")
    return fname


def save_tailored_resume_pdf(tailor_result: dict, company: str, role: str) -> Path:
    """Generate a simple tailored resume PDF."""
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import cm
        from reportlab.lib import colors
    except ImportError:
        print("[Tailorer] reportlab not installed — skipping PDF generation")
        return None

    profile = load_profile()
    TAILORED_DIR.mkdir(parents=True, exist_ok=True)

    safe_company = re.sub(r'[^\w]', '_', company)[:30]
    fname = TAILORED_DIR / f"resume_{safe_company}_{int(time.time())}.pdf"

    doc = SimpleDocTemplate(str(fname), pagesize=A4,
                            rightMargin=2*cm, leftMargin=2*cm,
                            topMargin=2*cm, bottomMargin=2*cm)
    styles = getSampleStyleSheet()
    story = []

    # Name header
    name_style = ParagraphStyle('Name', fontSize=20, fontName='Helvetica-Bold',
                                 spaceAfter=4, textColor=colors.HexColor('#1a1a2e'))
    story.append(Paragraph(profile.get('name', 'Candidate Name'), name_style))

    # Contact
    contact_parts = []
    if profile.get('email'):
        contact_parts.append(profile['email'])
    if profile.get('phone'):
        contact_parts.append(profile['phone'])
    if profile.get('linkedin'):
        contact_parts.append(profile['linkedin'])
    if contact_parts:
        story.append(Paragraph(" | ".join(contact_parts), styles['Normal']))
    story.append(Spacer(1, 0.3*cm))

    # Tailored summary
    section_style = ParagraphStyle('Section', fontSize=11, fontName='Helvetica-Bold',
                                    spaceAfter=4, spaceBefore=10,
                                    textColor=colors.HexColor('#7c3aed'))
    story.append(Paragraph("PROFESSIONAL SUMMARY", section_style))
    story.append(Paragraph(tailor_result.get('summary', ''), styles['Normal']))
    story.append(Spacer(1, 0.3*cm))

    # Skills (highlighted for this role)
    story.append(Paragraph("SKILLS", section_style))
    skills = tailor_result.get('skills_to_highlight', [])
    if not skills:
        skills = profile.get('skills', [])
    story.append(Paragraph(" • ".join(skills[:15]), styles['Normal']))
    story.append(Spacer(1, 0.3*cm))

    # Experience section (from profile)
    story.append(Paragraph("EXPERIENCE", section_style))
    companies = profile.get('companies', [])
    exp_text = f"{profile.get('years_experience', '')} years of experience"
    if companies:
        exp_text += f" at {', '.join(companies[:3])}"
    story.append(Paragraph(exp_text, styles['Normal']))
    story.append(Spacer(1, 0.3*cm))

    # Education
    edu = profile.get('education', [])
    if edu:
        story.append(Paragraph("EDUCATION", section_style))
        for e in edu[:2]:
            story.append(Paragraph(e, styles['Normal']))

    # ATS keywords footer
    ats_kw = tailor_result.get('ats_keywords', [])
    if ats_kw:
        story.append(Spacer(1, 0.5*cm))
        kw_style = ParagraphStyle('KW', fontSize=7, textColor=colors.white,
                                   backColor=colors.white)
        story.append(Paragraph(" ".join(ats_kw), kw_style))  # Hidden white text for ATS

    doc.build(story)
    print(f"[Tailorer] Resume PDF saved: {fname}")
    return fname


def tailor_for_job(jd_text: str, company: str, role: str) -> dict:
    """Full pipeline: tailor + save files. Returns paths + content."""
    print(f"[Tailorer] Tailoring for {role} at {company}...")
    result = tailor_resume_text(jd_text, company, role)

    cover_path = save_cover_letter_txt(result["cover_letter"], company, role)
    pdf_path = save_tailored_resume_pdf(result, company, role)

    result["cover_letter_path"] = str(cover_path) if cover_path else None
    result["resume_pdf_path"] = str(pdf_path) if pdf_path else None
    result["company"] = company
    result["role"] = role

    return result


import re  # needed for safe_company


if __name__ == "__main__":
    sample_jd = """
    Senior Python Developer — TechCorp Bangalore
    We need a developer with 4+ years in Python, FastAPI, PostgreSQL, Docker, AWS.
    You will build scalable microservices and work with ML teams.
    Strong problem solving and communication skills required.
    """
    result = tailor_for_job(sample_jd, "TechCorp", "Senior Python Developer")
    print("\n=== Tailor Result ===")
    print(f"Summary: {result['summary'][:200]}")
    print(f"Skills to highlight: {result['skills_to_highlight']}")
    print(f"Cover letter path: {result.get('cover_letter_path')}")
    print(f"Resume PDF path: {result.get('resume_pdf_path')}")
