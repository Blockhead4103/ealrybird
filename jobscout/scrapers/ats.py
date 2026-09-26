"""Anbindungen an verbreitete Bewerbermanagement-Systeme (ATS).

Viele grosse Firmen betreiben ihre Karriereseite nicht selbst, sondern über ein ATS.
Mehrere ATS bieten öffentliche JSON/XML-Schnittstellen an – das ist stabiler und
schonender als HTML zu "scrapen". Jede Funktion bekommt die Firma und einen Filter
`wanted(titel) -> bool`, damit Details nur für relevante Stellen geladen werden.

Hinweis: Die Formate stammen aus den öffentlichen Dokumentationen bzw. (Workday)
aus beobachtetem Verhalten. Anbieter können sie ändern – bei Fehlern bitte die
Meldung im Protokoll prüfen.
"""
from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from datetime import date, timedelta
from typing import Callable

from ..models import Company, Job
from . import http
from .util import html_to_text, parse_date

Wanted = Callable[[str], bool]
MAX_DETAILS = 60  # Obergrenze Detail-Abrufe pro Firma


def smartrecruiters(company: Company, wanted: Wanted) -> list[Job]:
    # https://developers.smartrecruiters.com/docs/posting-api
    base = f"https://api.smartrecruiters.com/v1/companies/{company.target}/postings"
    jobs, offset = [], 0
    while True:
        data = http.get(base, params={"limit": 100, "offset": offset}).json()
        content = data.get("content", [])
        for item in content:
            if not wanted(item.get("name", "")) or len(jobs) >= MAX_DETAILS:
                continue
            detail = http.get(f"{base}/{item['id']}").json()
            sections = (detail.get("jobAd") or {}).get("sections") or {}
            description = "\n".join(
                html_to_text((sections.get(key) or {}).get("text", ""))
                for key in ("jobDescription", "qualifications", "additionalInformation")
            )
            loc = item.get("location") or {}
            jobs.append(
                Job(
                    company=company.name,
                    title=item.get("name", ""),
                    url=detail.get("postingUrl") or f"https://jobs.smartrecruiters.com/{company.target}/{item['id']}",
                    location=", ".join(filter(None, [loc.get("city"), loc.get("country")])),
                    description=description,
                    posted=parse_date(item.get("releasedDate")),
                )
            )
        offset += len(content)
        if not content or offset >= data.get("totalFound", 0):
            return jobs


def greenhouse(company: Company, wanted: Wanted) -> list[Job]:
    # https://developers.greenhouse.io/job-board.html
    url = f"https://boards-api.greenhouse.io/v1/boards/{company.target}/jobs"
    data = http.get(url, params={"content": "true"}).json()
    jobs = []
    for item in data.get("jobs", []):
        if not wanted(item.get("title", "")):
            continue
        # "content" ist HTML, das zusätzlich HTML-escaped geliefert wird
        content = html_to_text(html_to_text(item.get("content", "")))
        jobs.append(
            Job(
                company=company.name,
                title=item.get("title", ""),
                url=item.get("absolute_url", ""),
                location=(item.get("location") or {}).get("name", ""),
                description=content,
                posted=parse_date(item.get("first_published") or item.get("updated_at")),
            )
        )
    return jobs


def lever(company: Company, wanted: Wanted) -> list[Job]:
    # https://github.com/lever/postings-api
    data = http.get(f"https://api.lever.co/v0/postings/{company.target}", params={"mode": "json"}).json()
    jobs = []
    for item in data:
        if not wanted(item.get("text", "")):
            continue
        parts = [item.get("descriptionPlain", "")]
        for block in item.get("lists", []):
            parts.append(block.get("text", ""))
            parts.append(html_to_text(block.get("content", "")))
        parts.append(item.get("additionalPlain", ""))
        jobs.append(
            Job(
                company=company.name,
                title=item.get("text", ""),
                url=item.get("hostedUrl", ""),
                location=(item.get("categories") or {}).get("location", ""),
                description="\n".join(p for p in parts if p),
                posted=parse_date(item.get("createdAt")),
            )
        )
    return jobs


def personio(company: Company, wanted: Wanted) -> list[Job]:
    # XML-Feed: https://<firma>.jobs.personio.de/xml  (Domain ggf. .com – in companies.yaml via "domain")
    domain = company.extra.get("domain", "jobs.personio.de")
    root = ET.fromstring(http.get(f"https://{company.target}.{domain}/xml").content)
    jobs = []
    for pos in root.iter("position"):
        title = pos.findtext("name", "")
        if not wanted(title):
            continue
        parts = []
        for jd in pos.iter("jobDescription"):
            parts.append(jd.findtext("name", ""))
            parts.append(html_to_text(jd.findtext("value", "")))
        job_id = pos.findtext("id", "")
        jobs.append(
            Job(
                company=company.name,
                title=title,
                url=f"https://{company.target}.{domain}/job/{job_id}",
                location=pos.findtext("office", ""),
                description="\n".join(p for p in parts if p),
                posted=parse_date(pos.findtext("createdAt")),
            )
        )
    return jobs


def recruitee(company: Company, wanted: Wanted) -> list[Job]:
    # https://docs.recruitee.com/reference/offers
    data = http.get(f"https://{company.target}.recruitee.com/api/offers/").json()
    jobs = []
    for item in data.get("offers", []):
        if not wanted(item.get("title", "")):
            continue
        jobs.append(
            Job(
                company=company.name,
                title=item.get("title", ""),
                url=item.get("careers_url", ""),
                location=item.get("location", ""),
                description=html_to_text(item.get("description", "")) + "\n" + html_to_text(item.get("requirements", "")),
                posted=parse_date(item.get("published_at") or item.get("created_at")),
            )
        )
    return jobs


def _workday_posted(text: str, today: date | None = None) -> date | None:
    """Workday liefert 'Posted Today', 'Posted Yesterday', 'Posted 3 Days Ago', 'Posted 30+ Days Ago'."""
    today = today or date.today()
    text = (text or "").lower()
    if "today" in text:
        return today
    if "yesterday" in text:
        return today - timedelta(days=1)
    m = re.search(r"(\d+)\+?\s*day", text)
    return today - timedelta(days=int(m.group(1))) if m else None


def workday(company: Company, wanted: Wanted) -> list[Job]:
    """target = URL der Workday-Jobseite, z.B. https://firma.wd3.myworkdayjobs.com/de-DE/Careers
    Nutzt die (inoffizielle) JSON-Schnittstelle, die auch die Workday-Webseite selbst verwendet."""
    m = re.match(r"https://([^./]+)\.(wd\d+)\.myworkdayjobs\.com/(?:[a-z]{2}-[A-Z]{2}/)?([^/?#]+)", company.target)
    if not m:
        raise ValueError(f"{company.name}: Workday-URL nicht erkannt: {company.target}")
    tenant, wd, site = m.groups()
    api = f"https://{tenant}.{wd}.myworkdayjobs.com/wday/cxs/{tenant}/{site}"
    jobs, offset, total = [], 0, None
    while len(jobs) < MAX_DETAILS:
        data = http.post_json(f"{api}/jobs", {"appliedFacets": {}, "limit": 20, "offset": offset, "searchText": ""}).json()
        postings = data.get("jobPostings", [])
        for item in postings:
            if not wanted(item.get("title", "")) or len(jobs) >= MAX_DETAILS:
                continue
            path = item.get("externalPath", "")
            info = http.get(f"{api}{path}", headers={"Accept": "application/json"}).json().get("jobPostingInfo", {})
            jobs.append(
                Job(
                    company=company.name,
                    title=item.get("title", ""),
                    url=info.get("externalUrl") or f"https://{tenant}.{wd}.myworkdayjobs.com/{site}{path}",
                    location=item.get("locationsText", ""),
                    description=html_to_text(info.get("jobDescription", "")),
                    posted=parse_date(info.get("startDate")) or _workday_posted(item.get("postedOn", "")),
                )
            )
        if total is None:  # Workday meldet "total" zuverlässig nur auf der ersten Seite
            total = data.get("total", 0)
        offset += len(postings)
        if not postings or offset >= total:
            break
    return jobs
