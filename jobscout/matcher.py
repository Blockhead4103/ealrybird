"""Vergleicht CV und Stellen.

Jede Anforderung aus dem Inserat ist eine Gruppe von Alternativen ("Studium in Recht oder BWL"):
sie gilt als erfüllt, wenn EINE Alternative im CV vorkommt.

Anforderungen werden in zwei Arten geteilt:
  Kern:   fachliche Anforderungen (Verkauf, Python, Laborautomation, Studienrichtung …)
  Basis:  was fast jedes CV erfüllt (Sprachen, Excel, "irgendein Abschluss", Führerausweis …)

Score (0–100), bewusst einfach und nachvollziehbar:
  60 % Anteil erfüllter Kern-Anforderungen
  10 % Anteil erfüllter Basis-Anforderungen
  15 % Anteil erfüllter Nice-to-haves
  15 % Titel-Treffer: Wörter aus dem Jobtitel, die im CV vorkommen
Begrenzungen:
  - Keine einzige Kern-Anforderung erfüllt      -> höchstens NO_CORE_CAP
  - Nur Basis-Anforderungen erkannt (unsicher)   -> höchstens BASIC_ONLY_CAP
  - Verlangte Studienrichtung / Doktorat fehlt   -> höchstens KNOCKOUT_CAP + Warnung
Anforderungszeilen ohne erkannten Skill fliessen NICHT in den Score ein, werden aber als
"selbst prüfen" angezeigt.
"""
from __future__ import annotations

import re

from .models import Job, Match, Requirement
from .skills import RELATED_FIELDS, cv_degree_fields, find_skills

KNOCKOUT_CAP = 40.0
NO_CORE_CAP = 30.0
BASIC_ONLY_CAP = 35.0
BASIC_SKILLS = {"Deutsch", "Englisch", "Französisch", "Italienisch", "Schweizerdeutsch", "Hochschulabschluss",
                "Lehre / EFZ", "Eidg. Fachausweis", "Führerausweis", "Excel", "Stakeholder Management"}
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


def _is_basic(req: Requirement) -> bool:
    return all(o in BASIC_SKILLS for o in req.options)


def _ratio(ok: list, total: list, default: float) -> float:
    return len(ok) / len(total) if total else default


def score_job(job: Job, cv_text: str, cv_have: set[str]) -> Match:
    lower_cv = cv_text.lower()

    def has(option: str) -> bool:  # KI-Skills sind freie Begriffe -> zusätzlich Textsuche
        return option in cv_have or option.lower() in lower_cv

    def met(req: Requirement) -> bool:
        if any(has(o) for o in req.options):
            return True
        if req.related_ok:  # "oder verwandte Richtung": Studium aus derselben Gruppe genügt
            wanted = set(req.options)
            return any(group & wanted and group & cv_have for group in RELATED_FIELDS)
        return False

    reqs = _requirements(job)
    must = [r for r in reqs if not r.nice]
    nice = [r for r in reqs if r.nice]
    core = [r for r in must if not _is_basic(r)]
    basic = [r for r in must if _is_basic(r)]
    core_ok = [r for r in core if met(r)]
    basic_ok = [r for r in basic if met(r)]
    nice_ok = [r for r in nice if met(r)]

    words = _title_words(job.title)
    title_ratio = sum(w in lower_cv for w in words) / len(words) if words else 0.0

    if core:
        core_ratio = len(core_ok) / len(core)
        score = (60 * core_ratio + 10 * _ratio(basic_ok, basic, core_ratio)
                 + 15 * _ratio(nice_ok, nice, core_ratio) + 15 * title_ratio)
        if not core_ok:
            score = min(score, NO_CORE_CAP)
    elif basic:
        score = min(BASIC_ONLY_CAP, 10 * _ratio(basic_ok, basic, 0) + 10 * _ratio(nice_ok, nice, 0) + 15 * title_ratio)
    else:
        job_skills = set(find_skills(job.description))
        overlap = len(job_skills & cv_have) / len(job_skills) if job_skills else 0.0
        score = min(BASIC_ONLY_CAP, 20 * overlap + 15 * title_ratio)

    if must:
        matched = [r.label for r in must if met(r)] + [f"{r.label} (Plus)" for r in nice_ok]
        missing = [r.label for r in must if not met(r)]
    else:
        job_skills = set(find_skills(job.description))
        matched, missing = sorted(job_skills & cv_have), sorted(job_skills - cv_have)

    knockout = [
        f"Verlangt: {r.label}"
        for r in must
        if not met(r) and r.kind == "degree" and any(o.startswith("Studium ") or o == "Doktorat / PhD" for o in r.options)
    ]
    if knockout:
        score = min(score, KNOCKOUT_CAP)
    return Match(job=job, score=round(score, 1), matched=matched, missing=missing, knockout=knockout, unchecked=list(job.unchecked))


def rank(jobs: list[Job], cv_text: str) -> list[Match]:
    cv_have = cv_profile(cv_text)
    # Stellen mit Ausschlusskriterium immer nach allen anderen
    return sorted((score_job(j, cv_text, cv_have) for j in jobs), key=lambda m: (not m.knockout, m.score), reverse=True)
