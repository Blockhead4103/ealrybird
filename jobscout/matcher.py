"""Vergleicht CV und Stellen.

Jede Anforderung aus dem Inserat ist eine Gruppe von Alternativen ("Studium in Recht oder BWL"):
sie gilt als erfüllt, wenn EINE Alternative im CV vorkommt.

Score (0–100), bewusst einfach und nachvollziehbar:
  70 % Anteil der erfüllten Pflicht-Anforderungen
  20 % Anteil der erfüllten Nice-to-have-Anforderungen
  10 % Titel-Treffer: Wörter aus dem Jobtitel, die im CV vorkommen
Ausschlusskriterium: Verlangt das Inserat eine bestimmte Studienrichtung, die im CV nicht vorkommt,
wird der Score auf höchstens KNOCKOUT_CAP begrenzt und die Stelle markiert.
Anforderungszeilen ohne erkannten Skill fliessen NICHT in den Score ein, werden aber als
"selbst prüfen" angezeigt.
"""
from __future__ import annotations

import re

from .models import Job, Match, Requirement
from .skills import cv_degree_fields, find_skills

KNOCKOUT_CAP = 40.0
STOPWORDS = {"und", "and", "the", "der", "die", "das", "for", "mit", "with", "m", "w", "d", "f", "x", "h", "in", "im",
             "senior", "junior", "lead", "head", "of", "sr", "jr", "100", "80", "60", "a", "an", "de", "la", "le", "et"}


def _title_words(title: str) -> set[str]:
    return {w for w in re.findall(r"[a-zäöüéèà]+", title.lower()) if len(w) > 2 and w not in STOPWORDS}


def cv_profile(cv_text: str) -> set[str]:
    return set(find_skills(cv_text)) | set(cv_degree_fields(cv_text))


def _requirements(job: Job) -> list[Requirement]:
    if job.requirements:
        return job.requirements
    # Fallback für Jobs, die nur must_have/nice_to_have-Listen haben (z.B. aus der KI)
    return [Requirement([m]) for m in job.must_have] + [Requirement([n], nice=True) for n in job.nice_to_have]


def score_job(job: Job, cv_text: str, cv_have: set[str]) -> Match:
    lower_cv = cv_text.lower()

    def has(option: str) -> bool:  # KI-Skills sind freie Begriffe -> zusätzlich Textsuche
        return option in cv_have or option.lower() in lower_cv

    reqs = _requirements(job)
    must = [r for r in reqs if not r.nice]
    nice = [r for r in reqs if r.nice]
    must_ok = [r for r in must if any(has(o) for o in r.options)]
    must_missing = [r for r in must if r not in must_ok]
    nice_ok = [r for r in nice if any(has(o) for o in r.options)]

    words = _title_words(job.title)
    title_ratio = sum(w in lower_cv for w in words) / len(words) if words else 0.0

    if must:
        nice_ratio = len(nice_ok) / len(nice) if nice else len(must_ok) / len(must)
        score = 70 * len(must_ok) / len(must) + 20 * nice_ratio + 10 * title_ratio
        matched = [r.label for r in must_ok] + [f"{r.label} (Plus)" for r in nice_ok]
        missing = [r.label for r in must_missing]
    else:
        job_skills = set(find_skills(job.description))
        overlap = len(job_skills & cv_have) / len(job_skills) if job_skills else 0.0
        score = 90 * overlap + 10 * title_ratio
        matched = sorted(job_skills & cv_have)
        missing = sorted(job_skills - cv_have)

    knockout = [f"Verlangt: {r.label}" for r in must_missing if r.kind == "degree" and any(o.startswith("Studium ") for o in r.options)]
    if knockout:
        score = min(score, KNOCKOUT_CAP)
    return Match(job=job, score=round(score, 1), matched=matched, missing=missing, knockout=knockout, unchecked=list(job.unchecked))


def rank(jobs: list[Job], cv_text: str) -> list[Match]:
    cv_have = cv_profile(cv_text)
    return sorted((score_job(j, cv_text, cv_have) for j in jobs), key=lambda m: m.score, reverse=True)
