"""Der komplette Ablauf: scrapen -> filtern -> Skills erkennen -> mit CV abgleichen."""
from __future__ import annotations

from datetime import date, timedelta
from typing import Callable

from .config import load_companies
from .matcher import rank
from .models import Job, Match
from .scrapers import scrape_all
from .skills import extract_skills
from .storage import stamp_first_seen


def filter_age(jobs: list[Job], max_age_days: int, today: date | None = None) -> list[Job]:
    cutoff = (today or date.today()) - timedelta(days=max_age_days)
    return [j for j in jobs if j.effective_date is None or j.effective_date >= cutoff]


def find_jobs(
    titles: list[str],
    max_age_days: int,
    use_llm: bool = False,
    min_employees: int = 100,
    progress: Callable[[str], None] | None = None,
    swiss_only: bool = True,
) -> tuple[list[Job], list[str]]:
    companies = load_companies(min_employees=min_employees)
    jobs, errors = scrape_all(companies, titles, progress, swiss_only=swiss_only)
    stamp_first_seen(jobs)
    jobs = filter_age(jobs, max_age_days)
    for job in jobs:
        job.must_have, job.nice_to_have = extract_skills(job.description, use_llm=use_llm)
    return jobs, errors


def match_cv(jobs: list[Job], cv_text: str, min_score: float = 0, top: int = 20) -> list[Match]:
    return [m for m in rank(jobs, cv_text) if m.score >= min_score][:top]
