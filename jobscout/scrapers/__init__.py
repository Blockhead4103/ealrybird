from __future__ import annotations

import logging
import re
from concurrent.futures import ThreadPoolExecutor
from typing import Callable

from ..models import Company, Job
from . import ats
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


def title_filter(titles: list[str]) -> Callable[[str], bool]:
    """Ein Job passt, wenn ALLE Wörter mindestens eines Suchbegriffs im Titel vorkommen.
    Beispiel: "Data Engineer" passt auf "Senior Data Engineer (m/w/d)". Leere Liste = alles."""
    terms = [re.findall(r"\w+", t.lower()) for t in titles if t.strip()]
    if not terms:
        return lambda title: bool(title.strip())

    def wanted(title: str) -> bool:
        words = title.lower()
        return any(all(w in words for w in term) for term in terms)

    return wanted


def scrape_all(companies: list[Company], titles: list[str], progress: Callable[[str], None] | None = None) -> tuple[list[Job], list[str]]:
    """Scrapt alle Firmen parallel (4 gleichzeitig). Gibt (Jobs, Fehlermeldungen) zurück."""
    wanted = title_filter(titles)
    jobs: list[Job] = []
    errors: list[str] = []

    def run(company: Company):
        return company, SCRAPERS[company.source](company, wanted)

    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = [pool.submit(run, c) for c in companies]
        for company, future in zip(companies, futures):
            try:
                _, found = future.result()
                jobs.extend(found)
                msg = f"{company.name}: {len(found)} passende Stellen"
            except Exception as exc:  # eine kaputte Quelle soll den Rest nicht stoppen
                msg = f"{company.name}: FEHLER – {type(exc).__name__}: {exc}"
                errors.append(msg)
                log.warning(msg)
            if progress:
                progress(msg)
    return jobs, errors
