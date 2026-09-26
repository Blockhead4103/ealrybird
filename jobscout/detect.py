"""Erkennt, welches Bewerbersystem (ATS) hinter einer Karriereseite steckt,
und schlägt den passenden Eintrag für companies.yaml vor."""
from __future__ import annotations

import re

from .scrapers import http

PATTERNS = [
    ("workday", re.compile(r"https://[a-z0-9-]+\.wd\d+\.myworkdayjobs\.com/(?:[a-z]{2}-[A-Z]{2}/)?[A-Za-z0-9_-]+")),
    ("smartrecruiters", re.compile(r"(?:jobs|careers)\.smartrecruiters\.com/([A-Za-z0-9_-]+)")),
    ("greenhouse", re.compile(r"(?:boards|job-boards)\.greenhouse\.io/(?:embed/job_board(?:/js)?\?for=)?([a-z0-9_-]+)")),
    ("lever", re.compile(r"jobs\.lever\.co/([A-Za-z0-9_-]+)")),
    ("personio", re.compile(r"([a-z0-9-]+)\.jobs\.personio\.(de|com)")),
    ("recruitee", re.compile(r"([a-z0-9-]+)\.recruitee\.com")),
]
IGNORE = {"embed", "js", "api", "www", "static", "assets"}


def detect_in(text: str, url: str) -> dict | None:
    haystack = url + "\n" + text
    for source, pattern in PATTERNS:
        for m in pattern.finditer(haystack):
            if source == "workday":
                return {"source": "workday", "target": m.group(0)}
            slug = m.group(1)
            if slug.lower() in IGNORE:
                continue
            entry = {"source": source, "target": slug}
            if source == "personio":
                entry["domain"] = f"jobs.personio.{m.group(2)}"
            return entry
    if '"JobPosting"' in text or "'JobPosting'" in text:
        return {"source": "jsonld", "target": url}
    return None


def detect(url: str) -> dict:
    resp = http.get(url, check_robots=True)
    found = detect_in(resp.text, resp.url)
    if found:
        return found
    # Kein Treffer: trotzdem den allgemeinen Scraper vorschlagen (folgt Links mit passendem Jobtitel)
    return {"source": "jsonld", "target": url, "hinweis": "Kein bekanntes ATS erkannt – allgemeiner Modus, Ergebnis unsicher."}
