"""Erkennt Stellen, die sich nicht an ausgebildete Berufsleute richten:
Studierende/Praktika, Lehrstellen und Doktorats-Stellen. Standardmässig werden sie ausgeblendet."""
from __future__ import annotations

import re

STUDENT = "Studierende / Praktikum"
APPRENTICE = "Lehrstelle"
DOCTORAL = "Doktorat"

_TITLE = [
    (APPRENTICE, r"lernende\w*|lehrstelle\w*|lehre als|apprentice\w*|apprenticeship|berufslehre|schnupperlehre"),
    (DOCTORAL, r"doktorand\w*|phd student|phd candidate|phd position|doctoral"),
    (STUDENT, r"intern|interns|internship|praktikant\w*|praktikum|werkstudent\w*|student\w*|studierende\w*|stagiaire|"
              r"tirocinio|tirocinante|master thesis|masterarbeit|bachelorarbeit|bachelor thesis|ferienjob|summer job|hiwi"),
]
# Formulierungen im Inserat, die klar sagen: du musst (noch) eingeschrieben sein
_DESCRIPTION = (
    STUDENT,
    r"enrolled (?:in|at|during)|currently enrolled|student status|immatrikuliert|eingeschrieben (?:an|in|für)|"
    r"you are currently (?:a )?student|you are currently studying|laufendes studium|du studierst (?:aktuell|derzeit|noch)|"
    r"sie studieren (?:aktuell|derzeit|noch)|während deines studiums|während ihres studiums",
)


def classify(title: str, description: str = "") -> str | None:
    for level, pattern in _TITLE:
        if re.search(rf"(?<!\w)(?:{pattern})(?!\w)", title or "", re.IGNORECASE):
            return level
    level, pattern = _DESCRIPTION
    if re.search(pattern, (description or "").replace("’", "'"), re.IGNORECASE):
        return level
    return None
