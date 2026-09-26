"""Vergleicht CV und Stellen.

Score (0–100), bewusst einfach und nachvollziehbar:
  70 % Anteil der Must-Have-Skills, die im CV vorkommen
  20 % Anteil der Nice-to-have-Skills, die im CV vorkommen
  10 % Titel-Treffer: Wörter aus dem Jobtitel, die im CV vorkommen
Hat eine Stelle keine erkennbaren Must-Haves, zählt nur die allgemeine Skill-Überlappung.
"""
from __future__ import annotations

import re

from .models import Job, Match
from .skills import find_skills

STOPWORDS = {"und", "and", "the", "der", "die", "das", "for", "mit", "with", "m", "w", "d", "f", "x", "h", "in", "im",
             "senior", "junior", "lead", "head", "of", "sr", "jr", "100", "80", "60", "a", "an", "de", "la", "le", "et"}


def _title_words(title: str) -> set[str]:
    return {w for w in re.findall(r"[a-zäöüéèà]+", title.lower()) if len(w) > 2 and w not in STOPWORDS}


def score_job(job: Job, cv_text: str, cv_skills: set[str]) -> Match:
    must, nice = job.must_have, job.nice_to_have
    lower_cv = cv_text.lower()

    def has(skill: str) -> bool:  # LLM-Skills sind freie Begriffe -> zusätzlich Textsuche
        return skill in cv_skills or skill.lower() in lower_cv

    matched = [s for s in must if has(s)]
    missing = [s for s in must if not has(s)]
    nice_hit = [s for s in nice if has(s)]

    words = _title_words(job.title)
    title_ratio = sum(w in lower_cv for w in words) / len(words) if words else 0.0

    if must:
        score = 70 * len(matched) / len(must) + 20 * (len(nice_hit) / len(nice) if nice else len(matched) / len(must)) + 10 * title_ratio
    else:
        job_skills = set(find_skills(job.description))
        overlap = len(job_skills & cv_skills) / len(job_skills) if job_skills else 0.0
        score = 90 * overlap + 10 * title_ratio
        matched = sorted(job_skills & cv_skills)
        missing = sorted(job_skills - cv_skills)
    return Match(job=job, score=round(score, 1), matched=matched + [f"{s} (Plus)" for s in nice_hit], missing=missing)


def rank(jobs: list[Job], cv_text: str) -> list[Match]:
    cv_skills = set(find_skills(cv_text))
    return sorted((score_job(j, cv_text, cv_skills) for j in jobs), key=lambda m: m.score, reverse=True)
