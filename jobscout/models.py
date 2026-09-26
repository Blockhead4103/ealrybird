from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date


@dataclass
class Company:
    name: str
    employees: int | None  # None = unbekannt (Firma wurde bewusst manuell aufgenommen)
    source: str  # "smartrecruiters" | "greenhouse" | "lever" | "personio" | "recruitee" | "workday" | "jsonld"
    target: str  # Firmen-Kennung beim Anbieter oder URL der Karriereseite
    extra: dict = field(default_factory=dict)


@dataclass
class Requirement:
    """Eine Anforderung aus dem Inserat. Sie ist erfüllt, wenn EINE der Optionen im CV vorkommt
    (z.B. "Studium in Recht oder BWL" -> options=["Studium Recht", "Studium BWL / Business"])."""

    options: list[str]
    text: str = ""  # Originalzeile aus dem Inserat
    nice: bool = False
    kind: str = "skill"  # "skill" | "degree"
    related_ok: bool = False  # Inserat erlaubt "verwandte/vergleichbare" Studienrichtungen

    @property
    def label(self) -> str:
        return " oder ".join(self.options)


@dataclass
class Job:
    company: str
    title: str
    url: str
    location: str = ""
    description: str = ""
    posted: date | None = None  # Veröffentlichungsdatum laut Quelle
    first_seen: date | None = None  # wann JobScout die Stelle zum ersten Mal gesehen hat
    must_have: list[str] = field(default_factory=list)
    nice_to_have: list[str] = field(default_factory=list)
    requirements: list[Requirement] = field(default_factory=list)
    unchecked: list[str] = field(default_factory=list)  # Anforderungszeilen ohne erkannten Skill
    section_found: bool = True  # False = kein Anforderungs-Abschnitt gefunden, ganzer Text durchsucht
    level: str | None = None  # z.B. "Studierende / Praktikum", "Lehrstelle", "Doktorat" (siehe levels.py)

    @property
    def effective_date(self) -> date | None:
        """Datum für den Alters-Filter: Veröffentlichung, sonst erstes Auftauchen."""
        return self.posted or self.first_seen

    @property
    def key(self) -> str:
        return f"{self.company}|{self.url}"


@dataclass
class Match:
    job: Job
    score: float  # 0–100
    matched: list[str]
    missing: list[str]
    knockout: list[str] = field(default_factory=list)  # nicht erfüllte Pflicht-Studienrichtungen
    unchecked: list[str] = field(default_factory=list)  # selbst prüfen
