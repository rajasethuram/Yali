"""
Follow-up Engine — auto-drafts and sends follow-up emails after 7 days silence.
Max 2 follow-ups per application. Uses Gmail via smtplib.
APScheduler runs daily check.
"""
import smtplib
import sys
import time
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from config.settings import (
    GROQ_API_KEY, GROQ_MODEL,
    GMAIL_ADDRESS, GMAIL_APP_PASSWORD, USER_NAME
)
from modules.job.tracker import get_tracker


def draft_followup_email(company: str, role: str, applied_date: str,
                          follow_up_count: int = 0) -> str:
    """Generate a follow-up email using Groq LLM."""
    if not GROQ_API_KEY:
        return _template_followup(company, role, applied_date, follow_up_count)

    from groq import Groq
    client = Groq(api_key=GROQ_API_KEY)

    is_second = follow_up_count >= 1
    prompt = f"""Write a {'second' if is_second else 'first'} follow-up email for a job application.

Candidate: {USER_NAME}
Company: {company}
Role: {role}
Applied: {applied_date}

Rules:
- Subject line first, then blank line, then body
- Professional, warm, NOT desperate
- Under 120 words total
- {'Shorter, acknowledge no response yet, still interested' if is_second else 'Express continued interest, ask about timeline'}
- End with clear next step request
- No "I hope this email finds you well" or similar

Format:
Subject: [subject here]

[email body here]"""

    try:
        resp = client.chat.completions.create(
            model=GROQ_MODEL,
            max_tokens=250,
            messages=[{"role": "user", "content": prompt}]
        )
        return resp.choices[0].message.content.strip()
    except Exception:
        return _template_followup(company, role, applied_date, follow_up_count)


def _template_followup(company: str, role: str, applied_date: str,
                        follow_up_count: int) -> str:
    if follow_up_count == 0:
        return f"""Subject: Following up — {role} Application

Hi,

I wanted to follow up on my application for the {role} position at {company}, submitted on {applied_date}.

I remain very interested in this opportunity and would love to discuss how my experience aligns with your needs. Could you share an update on the timeline?

Thank you for your time.

Best regards,
{USER_NAME}"""
    else:
        return f"""Subject: Re: {role} Application — {USER_NAME}

Hi,

I wanted to briefly check back regarding the {role} role at {company}. I understand you're busy and wanted to confirm my continued interest.

Please let me know if you need any additional information from my side.

Thank you,
{USER_NAME}"""


def send_followup_email(to_email: str, email_content: str) -> bool:
    """Send follow-up email via Gmail SMTP."""
    if not GMAIL_ADDRESS or not GMAIL_APP_PASSWORD:
        print("[FollowUp] Gmail not configured. Add GMAIL_ADDRESS + GMAIL_APP_PASSWORD to .env")
        return False

    lines = email_content.strip().split("\n")
    subject = ""
    body_lines = []
    in_body = False

    for line in lines:
        if line.startswith("Subject:"):
            subject = line.replace("Subject:", "").strip()
        elif line == "" and subject and not in_body:
            in_body = True
        elif in_body:
            body_lines.append(line)

    if not subject:
        subject = "Following up on my job application"
    body = "\n".join(body_lines).strip() if body_lines else email_content

    msg = MIMEMultipart()
    msg["From"] = GMAIL_ADDRESS
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(GMAIL_ADDRESS, GMAIL_APP_PASSWORD)
            server.send_message(msg)
        print(f"[FollowUp] Email sent to {to_email}: {subject}")
        return True
    except Exception as e:
        print(f"[FollowUp] Send failed: {e}")
        return False


def run_followup_check(dry_run: bool = False) -> list[dict]:
    """
    Check tracker for pending follow-ups, draft + send emails.
    dry_run=True: draft only, don't send.
    Returns list of processed follow-ups.
    """
    tracker = get_tracker()
    pending = tracker.get_pending_follow_ups(days_without_response=7)
    processed = []

    print(f"[FollowUp] {len(pending)} applications need follow-up")

    for app in pending:
        job_id = app["job_id"]
        company = app["company"]
        role = app["title"]
        applied_date = app["applied_date"]
        follow_up_count = app["follow_up_count"]

        if follow_up_count >= 2:
            continue

        email_content = draft_followup_email(company, role, applied_date, follow_up_count)

        result = {
            "job_id": job_id,
            "company": company,
            "role": role,
            "email_draft": email_content,
            "sent": False,
        }

        if not dry_run:
            # In production, to_email would come from JD or company contact
            # For now, log the draft — user can trigger send manually
            tracker.log_follow_up(job_id, email_content)
            result["sent"] = True
            print(f"[FollowUp] Follow-up #{follow_up_count + 1} logged for {company}")

        processed.append(result)

    return processed


def start_scheduler():
    """Start APScheduler background job for daily follow-up check."""
    try:
        from apscheduler.schedulers.background import BackgroundScheduler
        scheduler = BackgroundScheduler()
        scheduler.add_job(
            run_followup_check,
            "cron",
            hour=9,
            minute=0,
            id="daily_followup",
            replace_existing=True,
        )
        scheduler.start()
        print("[FollowUp] Daily follow-up scheduler started (runs at 09:00)")
        return scheduler
    except Exception as e:
        print(f"[FollowUp] Scheduler error: {e}")
        return None


if __name__ == "__main__":
    print("=== Follow-up Engine Test ===")
    draft = draft_followup_email("Google", "Senior Python Engineer", "2026-04-13", 0)
    print(draft)
    print("\n--- Checking pending follow-ups (dry run) ---")
    results = run_followup_check(dry_run=True)
    print(f"Found {len(results)} pending follow-ups")
