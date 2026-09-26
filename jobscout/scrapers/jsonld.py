"""Allgemeiner Scraper für beliebige Karriereseiten über schema.org/JobPosting.

Viele Karriereseiten betten Stelleninfos als JSON-LD (<script type="application/ld+json">)
ein, damit Google for Jobs sie findet. Dieser Scraper
  1. lädt die Karriereseite (target),
  2. liest dort vorhandene JobPosting-Daten,
  3. folgt Links, deren Text zum gesuchten Jobtitel passt, und liest dort JobPosting-Daten.

Grenze: Seiten, die ihre Stellen erst per JavaScript nachladen, liefern hier nichts.
Dann lohnt es sich zu prüfen, ob die Firma eines der unterstützten ATS nutzt
(siehe README, Abschnitt "Neue Firma hinzufügen").
"""
from __future__ import annotations

import json
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

from ..models import Company, Job
from . import http
from .ats import MAX_DETAILS, Wanted
from .util import html_to_text, parse_date


def _iter_objects(data):
    if isinstance(data, list):
        for item in data:
            yield from _iter_objects(item)
    elif isinstance(data, dict):
        yield data
        if "@graph" in data:
            yield from _iter_objects(data["@graph"])


def _is_job_posting(obj: dict) -> bool:
    kind = obj.get("@type")
    return kind == "JobPosting" or (isinstance(kind, list) and "JobPosting" in kind)


def _location(obj: dict) -> str:
    loc = obj.get("jobLocation")
    if isinstance(loc, list):
        loc = loc[0] if loc else {}
    addr = (loc or {}).get("address", {}) if isinstance(loc, dict) else {}
    if isinstance(addr, str):
        return addr
    return ", ".join(filter(None, [addr.get("addressLocality"), addr.get("addressCountry") if isinstance(addr.get("addressCountry"), str) else None]))


def extract_postings(html: str, page_url: str, company: str) -> list[Job]:
    soup = BeautifulSoup(html, "html.parser")
    jobs = []
    for tag in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(tag.string or tag.get_text() or "")
        except (json.JSONDecodeError, TypeError):
            continue
        for obj in _iter_objects(data):
            if not _is_job_posting(obj):
                continue
            desc = html_to_text(obj.get("description", ""))
            for extra in ("qualifications", "skills", "experienceRequirements"):
                if isinstance(obj.get(extra), str):
                    desc += "\n" + html_to_text(obj[extra])
            jobs.append(
                Job(
                    company=company,
                    title=html_to_text(obj.get("title", "")),
                    url=obj.get("url") or page_url,
                    location=_location(obj),
                    description=desc,
                    posted=parse_date(obj.get("datePosted")),
                )
            )
    return jobs


def jsonld(company: Company, wanted: Wanted) -> list[Job]:
    start = company.target
    html = http.get(start, check_robots=True).text
    jobs = [j for j in extract_postings(html, start, company.name) if wanted(j.title)]

    host = urlparse(start).netloc
    soup = BeautifulSoup(html, "html.parser")
    seen = {start}
    for a in soup.find_all("a", href=True):
        if len(jobs) >= MAX_DETAILS:
            break
        link = urljoin(start, a["href"]).split("#")[0]
        if link in seen or urlparse(link).netloc != host or not wanted(a.get_text(" ", strip=True)):
            continue
        seen.add(link)
        try:
            detail = http.get(link, check_robots=True).text
        except Exception:
            continue
        found = extract_postings(detail, link, company.name)
        if not found:  # Kein JSON-LD: Titel = Linktext, Beschreibung = Seitentext
            body = BeautifulSoup(detail, "html.parser")
            for junk in body(["script", "style", "nav", "header", "footer"]):
                junk.decompose()
            found = [Job(company=company.name, title=a.get_text(" ", strip=True), url=link, description=html_to_text(str(body)))]
        jobs.extend(found)

    unique = {}
    for job in jobs:
        unique.setdefault(job.url, job)
    return list(unique.values())
