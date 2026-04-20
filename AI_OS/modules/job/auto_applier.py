"""
Auto-Applier — fills and submits job applications using Playwright.
Handles LinkedIn Easy Apply and Indeed Quick Apply.
Uses human-like delays and mouse movement for anti-detection.
"""
import asyncio
import json
import random
import sys
import time
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from config.settings import MEMORY_DIR
from modules.cognitive.resume_parser import load_profile
from modules.job.tracker import ApplicationTracker

APPLY_CONFIG_PATH = MEMORY_DIR / "apply_config.json"


def load_apply_config() -> dict:
    """Load user's application config (salary, notice period, etc.)"""
    defaults = {
        "notice_period_days": 30,
        "expected_salary_lpa": 15,
        "work_authorization": "Yes - Indian Citizen",
        "willing_to_relocate": True,
        "linkedin_email": "",
        "linkedin_password": "",
        "indeed_email": "",
        "indeed_password": "",
    }
    if APPLY_CONFIG_PATH.exists():
        with open(APPLY_CONFIG_PATH) as f:
            saved = json.load(f)
        defaults.update(saved)
    return defaults


def save_apply_config(config: dict):
    MEMORY_DIR.mkdir(parents=True, exist_ok=True)
    with open(APPLY_CONFIG_PATH, "w") as f:
        json.dump(config, f, indent=2)


async def _human_delay(min_ms: int = 800, max_ms: int = 2500):
    """Random human-like delay between actions."""
    await asyncio.sleep(random.uniform(min_ms / 1000, max_ms / 1000))


async def _human_type(page, selector: str, text: str):
    """Type text character by character with random delays."""
    await page.click(selector)
    await page.fill(selector, "")
    for char in text:
        await page.type(selector, char)
        await asyncio.sleep(random.uniform(0.05, 0.15))


async def apply_linkedin_easy_apply(
    job_url: str,
    job_id: str,
    company: str,
    role: str,
    resume_pdf_path: Optional[str] = None,
) -> dict:
    """Apply to a LinkedIn Easy Apply job."""
    profile = load_profile()
    config = load_apply_config()
    tracker = ApplicationTracker()

    result = {
        "job_id": job_id,
        "company": company,
        "role": role,
        "source": "linkedin",
        "status": "failed",
        "message": "",
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
    }

    if not config.get("linkedin_email") or not config.get("linkedin_password"):
        result["message"] = "LinkedIn credentials not configured. Add to apply_config.json"
        result["status"] = "skipped"
        return result

    try:
        from playwright.async_api import async_playwright
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=False)  # visible for debugging
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            )
            page = await context.new_page()

            # Login to LinkedIn
            await page.goto("https://www.linkedin.com/login")
            await _human_delay(1000, 2000)
            await _human_type(page, '#username', config["linkedin_email"])
            await _human_delay(500, 1200)
            await _human_type(page, '#password', config["linkedin_password"])
            await _human_delay(300, 800)
            await page.click('[type="submit"]')
            await _human_delay(2000, 4000)

            # Check login success
            if "login" in page.url or "checkpoint" in page.url:
                result["message"] = "LinkedIn login failed — check credentials"
                await browser.close()
                return result

            # Navigate to job
            await page.goto(job_url, timeout=30000)
            await _human_delay(2000, 3500)

            # Click Easy Apply button
            easy_apply_btn = await page.query_selector('.jobs-apply-button--top-card button, .artdeco-button--primary')
            if not easy_apply_btn:
                result["message"] = "Easy Apply button not found — manual apply required"
                result["status"] = "manual_required"
                await browser.close()
                return result

            await easy_apply_btn.click()
            await _human_delay(1500, 2500)

            # Handle multi-step form
            max_steps = 8
            for step in range(max_steps):
                await _human_delay(800, 1500)

                # Upload resume if prompted
                resume_input = await page.query_selector('input[type="file"]')
                if resume_input and resume_pdf_path and Path(resume_pdf_path).exists():
                    await resume_input.set_input_files(resume_pdf_path)
                    await _human_delay(1000, 2000)

                # Fill phone number
                phone_input = await page.query_selector('input[id*="phone"], input[id*="Phone"]')
                if phone_input and profile.get("phone"):
                    await _human_type(page, f'input[id*="phone"], input[id*="Phone"]',
                                     profile["phone"])

                # Handle common select dropdowns
                selects = await page.query_selector_all('select')
                for sel in selects:
                    label = await sel.evaluate('el => el.previousElementSibling?.textContent || el.getAttribute("aria-label") || ""')
                    label_lower = label.lower()

                    if "experience" in label_lower or "years" in label_lower:
                        exp_val = str(profile.get("years_experience", 3))
                        try:
                            await sel.select_option(value=exp_val)
                        except Exception:
                            await sel.select_option(index=min(profile.get("years_experience", 3), 5))

                    elif "authorization" in label_lower or "work" in label_lower:
                        try:
                            await sel.select_option(label="Yes")
                        except Exception:
                            pass

                    elif "relocat" in label_lower:
                        try:
                            await sel.select_option(label="Yes" if config.get("willing_to_relocate") else "No")
                        except Exception:
                            pass

                # Handle yes/no radio buttons for work authorization
                auth_radios = await page.query_selector_all('input[type="radio"]')
                for radio in auth_radios:
                    radio_label = await radio.evaluate('el => el.nextElementSibling?.textContent || ""')
                    if "yes" in radio_label.lower() and not await radio.is_checked():
                        container_text = await radio.evaluate('el => el.closest("[data-test-form-element]")?.textContent || ""')
                        if any(kw in container_text.lower() for kw in ["authorized", "eligible", "legally"]):
                            await radio.click()
                            await _human_delay(300, 600)

                # Check for salary/CTC field
                salary_inputs = await page.query_selector_all('input[id*="salary"], input[id*="ctc"], input[id*="compensation"]')
                for s_input in salary_inputs:
                    try:
                        await _human_type(page, f'input[id="{await s_input.get_attribute("id")}"]',
                                         str(config.get("expected_salary_lpa", 15) * 100000))
                    except Exception:
                        pass

                # Next / Submit button
                next_btn = await page.query_selector(
                    'button[aria-label="Submit application"], '
                    'button[aria-label="Review"], '
                    'button[aria-label="Next"], '
                    '.artdeco-button--primary'
                )

                if next_btn:
                    btn_text = await next_btn.inner_text()
                    await next_btn.click()
                    await _human_delay(1500, 3000)

                    if "submit" in btn_text.lower():
                        result["status"] = "applied"
                        result["message"] = "Application submitted successfully"
                        tracker.add_application(
                            job_id=job_id, company=company, title=role,
                            source="linkedin", apply_url=job_url
                        )
                        break
                else:
                    break

            if result["status"] != "applied":
                result["message"] = "Form navigation incomplete — may need manual completion"
                result["status"] = "partial"

            await _human_delay(1000, 2000)
            await browser.close()

    except Exception as e:
        result["message"] = f"Error: {e}"

    print(f"[AutoApply] LinkedIn {company}: {result['status']} — {result['message']}")
    return result


async def apply_indeed_quick_apply(
    job_url: str,
    job_id: str,
    company: str,
    role: str,
    resume_pdf_path: Optional[str] = None,
) -> dict:
    """Apply to an Indeed Quick Apply job."""
    profile = load_profile()
    config = load_apply_config()
    tracker = ApplicationTracker()

    result = {
        "job_id": job_id,
        "company": company,
        "role": role,
        "source": "indeed",
        "status": "failed",
        "message": "",
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
    }

    if not config.get("indeed_email") or not config.get("indeed_password"):
        result["message"] = "Indeed credentials not configured. Add to apply_config.json"
        result["status"] = "skipped"
        return result

    try:
        from playwright.async_api import async_playwright
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=False)
            page = await browser.new_page()

            # Login
            await page.goto("https://secure.indeed.com/account/login")
            await _human_delay(1500, 2500)
            await _human_type(page, 'input[name="email"], input[type="email"]',
                             config["indeed_email"])
            await _human_delay(400, 900)
            await page.click('button[type="submit"], .icl-Button')
            await _human_delay(1500, 2500)

            # Handle password page
            pwd_input = await page.query_selector('input[type="password"]')
            if pwd_input:
                await _human_type(page, 'input[type="password"]', config["indeed_password"])
                await _human_delay(300, 700)
                await page.click('button[type="submit"]')
                await _human_delay(2000, 3500)

            # Navigate to job
            await page.goto(job_url, timeout=30000)
            await _human_delay(2000, 3000)

            # Find Apply button
            apply_btn = await page.query_selector(
                '#indeedApplyButton, .jobsearch-IndeedApplyButton-newDesign, '
                'button[data-testid="IndeedApplyButton"]'
            )
            if not apply_btn:
                result["message"] = "Apply button not found"
                result["status"] = "manual_required"
                await browser.close()
                return result

            await apply_btn.click()
            await _human_delay(2000, 3500)

            # Indeed opens in popup — switch to it
            pages = context.pages if hasattr(context, 'pages') else [page]
            apply_page = pages[-1]

            # Fill form fields
            for field_id, value in [
                ('input[name="name"], input[id*="name"]', profile.get("name", "")),
                ('input[name="email"], input[type="email"]', profile.get("email", "")),
                ('input[name="phone"], input[id*="phone"]', profile.get("phone", "")),
            ]:
                try:
                    el = await apply_page.query_selector(field_id)
                    if el and value:
                        await _human_type(apply_page, field_id, value)
                        await _human_delay(200, 500)
                except Exception:
                    pass

            # Upload resume
            resume_upload = await apply_page.query_selector('input[type="file"]')
            if resume_upload and resume_pdf_path and Path(resume_pdf_path).exists():
                await resume_upload.set_input_files(resume_pdf_path)
                await _human_delay(1500, 2500)

            # Submit
            submit_btn = await apply_page.query_selector(
                'button[type="submit"], button[data-testid="submit-button"]'
            )
            if submit_btn:
                await submit_btn.click()
                await _human_delay(2000, 3500)
                result["status"] = "applied"
                result["message"] = "Application submitted"
                tracker.add_application(
                    job_id=job_id, company=company, title=role,
                    source="indeed", apply_url=job_url
                )
            else:
                result["message"] = "Submit button not found"
                result["status"] = "partial"

            await browser.close()

    except Exception as e:
        result["message"] = f"Error: {e}"

    print(f"[AutoApply] Indeed {company}: {result['status']} — {result['message']}")
    return result


async def apply_batch(jobs: list, resume_pdf_path: Optional[str] = None,
                      max_applications: int = 10) -> list[dict]:
    """Apply to a batch of scored jobs."""
    results = []
    applied_count = 0

    for job in jobs[:max_applications]:
        if applied_count >= max_applications:
            break

        source = job.get("source", "")
        url = job.get("apply_url", "")
        job_id = job.get("job_id", str(hash(url)))
        company = job.get("company", "Unknown")
        role = job.get("title", "Unknown")

        print(f"[AutoApply] Applying to {role} at {company} ({source})...")

        if source == "linkedin":
            res = await apply_linkedin_easy_apply(url, job_id, company, role, resume_pdf_path)
        elif source == "indeed":
            res = await apply_indeed_quick_apply(url, job_id, company, role, resume_pdf_path)
        else:
            res = {"status": "skipped", "message": f"Source {source} not supported for auto-apply",
                   "company": company, "role": role, "job_id": job_id}

        results.append(res)
        if res["status"] == "applied":
            applied_count += 1

        # Rate limit: wait 10-20s between applications
        if applied_count < max_applications:
            await asyncio.sleep(random.uniform(10, 20))

    print(f"[AutoApply] Done. Applied: {applied_count}/{len(jobs)} jobs processed")
    return results


if __name__ == "__main__":
    print("Auto-Applier module loaded.")
    print("Configure credentials: set linkedin_email/linkedin_password in memory/apply_config.json")
    cfg = load_apply_config()
    print(f"Current config keys: {list(cfg.keys())}")
