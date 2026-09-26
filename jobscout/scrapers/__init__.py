from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor
from typing import Callable

from ..models import Company, Job
from . import ats
from .filters import JobFilter
from .jsonld import jsonld

log = logging.getLogger(__name__)

SCRAPERS: dict[str, Callable] = {
    "smartrecruiters": ats.smartrecruiters,
    "greenhouse": ats.greenhouse,
    "lever": ats.lever,
    "personio": ats.personio,
    "recruitee": ats.recruitee,
    "workday": ats.workday,
    "jsonld": jsonld,
}


def title_filter(titles: list[str], swiss_only: bool = False) -> JobFilter:
    return JobFilter(titles, swiss_only)


def scrape_all(
    companies: list[Company],
    titles: list[str],
    progress: Callable[[str], None] | None = None,
    swiss_only: bool = True,
) -> tuple[list[Job], list[str]]:
    """Scrapt alle Firmen parallel (4 gleichzeitig). Gibt (Jobs, Fehlermeldungen) zurück."""
    wanted = JobFilter(titles, swiss_only)
    jobs: list[Job] = []
    errors: list[str] = []

    def run(company: Company):
        return company, SCRAPERS[company.source](company, wanted)

    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = [pool.submit(run, c) for c in companies]
        for company, future in zip(companies, futures):
            try:
                _, found = future.result()
                # Nachkontrolle: nach dem Laden der Details ist der Ort oft genauer bekannt
                found = [j for j in found if wanted.location_ok(j.location)]
                jobs.extend(found)
                msg = f"{company.name}: {len(found)} passende Stellen"
            except Exception as exc:  # eine kaputte Quelle soll den Rest nicht stoppen
                msg = f"{company.name}: FEHLER – {type(exc).__name__}: {exc}"
                errors.append(msg)
            if progress:
                progress(msg)
            elif msg in errors:
                log.warning(msg)
    return jobs, errors
