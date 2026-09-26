from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date


@dataclass
class Company:
    name: str
    employees: int
    source: str  # "smartrecruiters" | "greenhouse" | "lever" | "personio" | "recruitee" | "workday" | "jsonld"
    target: str  # Firmen-Kennung beim Anbieter oder URL der Karriereseite
    extra: dict = field(default_factory=dict)


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
