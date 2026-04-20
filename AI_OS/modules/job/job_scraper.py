"""
Job Scraper — scrapes LinkedIn, Indeed, Naukri for job listings.
Uses Playwright for JS-rendered pages, BeautifulSoup for static parsing.
"""
import asyncio
import json
import re
import sys
import time
from pathlib import Path
from typing import Optional
from dataclasses import dataclass, asdict

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from config.settings import MEMORY_DIR

@dataclass
class Job:
    title: str
    company: str
    location: str
    jd_text: str
    apply_url: str
    source: str
    date_scraped: str = ""
    job_id: str = ""
    salary: str = ""
    match_score: float = 0.0

    def to_dict(self):
        return asdict(self)


JOBS_CACHE_PATH = MEMORY_DIR / "scraped_jobs.json"


# ── Indeed Scraper (requests + BeautifulSoup, no login needed) ─────────────────

async def scrape_indeed(query: str, location: str = "", max_results: int = 20) -> list[Job]:
    """Scrape Indeed jobs using Playwright (handles JS rendering)."""
    jobs = []
    try:
        from playwright.async_api import async_playwright
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()

            loc_param = location.replace(" ", "+") if location else ""
            q_param = query.replace(" ", "+")
            url = f"https://in.indeed.com/jobs?q={q_param}&l={loc_param}"

            await page.goto(url, timeout=30000)
            await page.wait_for_timeout(2000)

            job_cards = await page.query_selector_all('[class*="job_seen_beacon"], [class*="tapItem"], .result')

            for card in job_cards[:max_results]:
                try:
                    title_el = await card.query_selector('h2 a span, .jobTitle span')
                    company_el = await card.query_selector('[data-testid="company-name"], .companyName')
                    location_el = await card.query_selector('[data-testid="text-location"], .companyLocation')
                    link_el = await card.query_selector('h2 a')

                    title = await title_el.inner_text() if title_el else "Unknown"
                    company = await company_el.inner_text() if company_el else "Unknown"
                    loc = await location_el.inner_text() if location_el else location
                    href = await link_el.get_attribute('href') if link_el else ""
                    apply_url = f"https://in.indeed.com{href}" if href and href.startswith('/') else href

                    # Get JD text
                    jd_text = ""
                    if apply_url:
                        try:
                            jd_page = await browser.new_page()
                            await jd_page.goto(apply_url, timeout=15000)
                            await jd_page.wait_for_timeout(1500)
                            jd_el = await jd_page.query_selector('#jobDescriptionText, .jobsearch-jobDescriptionText')
                            if jd_el:
                                jd_text = await jd_el.inner_text()
                            await jd_page.close()
                        except Exception:
                            pass

                    jobs.append(Job(
                        title=title.strip(),
                        company=company.strip(),
                        location=loc.strip(),
                        jd_text=jd_text[:3000],
                        apply_url=apply_url,
                        source="indeed",
                        date_scraped=time.strftime("%Y-%m-%d"),
                        job_id=f"indeed_{hash(apply_url) % 99999}",
                    ))
                except Exception:
                    continue

            await browser.close()
    except Exception as e:
        print(f"[Scraper] Indeed error: {e}")

    print(f"[Scraper] Indeed: found {len(jobs)} jobs for '{query}'")
    return jobs


# ── LinkedIn Scraper (public search, no login needed for basic results) ────────

async def scrape_linkedin(query: str, location: str = "", max_results: int = 20) -> list[Job]:
    """Scrape LinkedIn public job search."""
    jobs = []
    try:
        from playwright.async_api import async_playwright
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            )

            q_param = query.replace(" ", "%20")
            loc_param = location.replace(" ", "%20")
            url = f"https://www.linkedin.com/jobs/search/?keywords={q_param}&location={loc_param}"

            await page.goto(url, timeout=30000)
            await page.wait_for_timeout(3000)

            job_cards = await page.query_selector_all('.job-search-card, .jobs-search__results-list li')

            for card in job_cards[:max_results]:
                try:
                    title_el = await card.query_selector('h3, .base-search-card__title')
                    company_el = await card.query_selector('h4, .base-search-card__subtitle')
                    location_el = await card.query_selector('.job-search-card__location, .base-search-card__metadata')
                    link_el = await card.query_selector('a.base-card__full-link, a[href*="/jobs/view/"]')

                    title = await title_el.inner_text() if title_el else "Unknown"
                    company = await company_el.inner_text() if company_el else "Unknown"
                    loc = await location_el.inner_text() if location_el else location
                    apply_url = await link_el.get_attribute('href') if link_el else ""
                    if apply_url and '?' in apply_url:
                        apply_url = apply_url.split('?')[0]

                    jd_text = ""
                    if apply_url:
                        try:
                            jd_page = await browser.new_page()
                            await jd_page.goto(apply_url, timeout=15000)
                            await jd_page.wait_for_timeout(2000)
                            jd_el = await jd_page.query_selector('.show-more-less-html__markup, .description__text')
                            if jd_el:
                                jd_text = await jd_el.inner_text()
                            await jd_page.close()
                        except Exception:
                            pass

                    jobs.append(Job(
                        title=title.strip(),
                        company=company.strip(),
                        location=loc.strip(),
                        jd_text=jd_text[:3000],
                        apply_url=apply_url,
                        source="linkedin",
                        date_scraped=time.strftime("%Y-%m-%d"),
                        job_id=f"linkedin_{hash(apply_url) % 99999}",
                    ))
                except Exception:
                    continue

            await browser.close()
    except Exception as e:
        print(f"[Scraper] LinkedIn error: {e}")

    print(f"[Scraper] LinkedIn: found {len(jobs)} jobs for '{query}'")
    return jobs


# ── Naukri Scraper ─────────────────────────────────────────────────────────────

async def scrape_naukri(query: str, location: str = "", max_results: int = 20) -> list[Job]:
    """Scrape Naukri.com job listings."""
    jobs = []
    try:
        from playwright.async_api import async_playwright
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()

            q_param = query.replace(" ", "-")
            loc_param = location.replace(" ", "-").lower() if location else ""
            if loc_param:
                url = f"https://www.naukri.com/{q_param}-jobs-in-{loc_param}"
            else:
                url = f"https://www.naukri.com/{q_param}-jobs"

            await page.goto(url, timeout=30000)
            await page.wait_for_timeout(3000)

            job_cards = await page.query_selector_all('.jobTuple, article.jobTupleHeader, .cust-job-tuple')

            for card in job_cards[:max_results]:
                try:
                    title_el = await card.query_selector('a.title, .jobTitle a')
                    company_el = await card.query_selector('.companyInfo a, .comp-name')
                    location_el = await card.query_selector('.locWdth, .loc span')
                    link_el = await card.query_selector('a.title, .jobTitle a')

                    title = await title_el.inner_text() if title_el else "Unknown"
                    company = await company_el.inner_text() if company_el else "Unknown"
                    loc = await location_el.inner_text() if location_el else location
                    apply_url = await link_el.get_attribute('href') if link_el else ""

                    jobs.append(Job(
                        title=title.strip(),
                        company=company.strip(),
                        location=loc.strip(),
                        jd_text="",
                        apply_url=apply_url,
                        source="naukri",
                        date_scraped=time.strftime("%Y-%m-%d"),
                        job_id=f"naukri_{hash(apply_url) % 99999}",
                    ))
                except Exception:
                    continue

            await browser.close()
    except Exception as e:
        print(f"[Scraper] Naukri error: {e}")

    print(f"[Scraper] Naukri: found {len(jobs)} jobs for '{query}'")
    return jobs


# ── Master Search ──────────────────────────────────────────────────────────────

async def search_jobs(
    query: str,
    location: str = "",
    sources: Optional[list] = None,
    max_per_source: int = 15,
) -> list[Job]:
    """Search across all job boards simultaneously."""
    sources = sources or ["linkedin", "indeed", "naukri"]

    tasks = []
    if "indeed" in sources:
        tasks.append(scrape_indeed(query, location, max_per_source))
    if "linkedin" in sources:
        tasks.append(scrape_linkedin(query, location, max_per_source))
    if "naukri" in sources:
        tasks.append(scrape_naukri(query, location, max_per_source))

    results = await asyncio.gather(*tasks, return_exceptions=True)

    all_jobs = []
    for result in results:
        if isinstance(result, list):
            all_jobs.extend(result)

    # Deduplicate by title+company
    seen = set()
    unique_jobs = []
    for job in all_jobs:
        key = f"{job.title.lower()}_{job.company.lower()}"
        if key not in seen:
            seen.add(key)
            unique_jobs.append(job)

    # Cache results
    _save_jobs(unique_jobs)
    print(f"[Scraper] Total unique jobs found: {len(unique_jobs)}")
    return unique_jobs


def _save_jobs(jobs: list[Job]):
    MEMORY_DIR.mkdir(parents=True, exist_ok=True)
    data = [j.to_dict() for j in jobs]
    with open(JOBS_CACHE_PATH, "w") as f:
        json.dump(data, f, indent=2)


def load_cached_jobs() -> list[dict]:
    if JOBS_CACHE_PATH.exists():
        with open(JOBS_CACHE_PATH) as f:
            return json.load(f)
    return []


if __name__ == "__main__":
    import sys
    query = sys.argv[1] if len(sys.argv) > 1 else "Python developer"
    location = sys.argv[2] if len(sys.argv) > 2 else "Bangalore"

    async def main():
        jobs = await search_jobs(query, location, sources=["indeed"], max_per_source=5)
        print(f"\n=== Found {len(jobs)} jobs ===")
        for j in jobs[:5]:
            print(f"  [{j.source}] {j.title} @ {j.company} — {j.location}")
            print(f"    URL: {j.apply_url[:80]}")

    asyncio.run(main())
