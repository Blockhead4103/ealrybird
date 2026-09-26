"""Filter nach Jobtitel und Standort (Schweiz), angewendet BEVOR Stellendetails geladen werden."""
from __future__ import annotations

import re

SWISS_WORDS = [
    "switzerland", "schweiz", "suisse", "svizzera", "svizra", "confoederatio helvetica",
    "zürich", "zurich", "basel", "bern", "berne", "genf", "geneva", "genève", "geneve", "lausanne", "luzern", "lucerne",
    "zug", "st. gallen", "st gallen", "winterthur", "lugano", "baar", "schlieren", "rotkreuz", "kaiseraugst", "visp",
    "neuchâtel", "neuchatel", "fribourg", "freiburg im üechtland", "aarau", "baden", "olten", "solothurn", "chur", "sion",
    "thun", "biel", "bienne", "schaffhausen", "wallisellen", "dübendorf", "rapperswil", "allschwil", "muttenz", "pratteln",
    "risch", "cham", "steinhausen", "bulle", "nyon", "vevey", "monthey", "yverdon", "la chaux-de-fonds", "le locle",
    "bellinzona", "locarno", "mendrisio", "kloten", "opfikon", "glattbrugg", "regensdorf", "horgen", "ittigen",
    "plan-les-ouates", "meyrin", "epalinges", "ecublens", "renens", "morges", "rolle", "gland", "martigny", "stein am rhein",
    "burgdorf", "langenthal", "wil", "frauenfeld", "kreuzlingen", "arbon", "uzwil", "schindellegi", "pfäffikon", "altdorf",
    "stans", "sarnen", "herisau", "appenzell", "glarus", "liestal", "delémont", "delemont", "porrentruy", "wädenswil",
]
_SWISS = re.compile(r"(?<!\w)(?:" + "|".join(re.escape(w) for w in SWISS_WORDS) + r"|ch|che)(?!\w)", re.IGNORECASE)


def is_swiss(location: str) -> bool | None:
    """True/False, wenn der Ort eindeutig ist; None, wenn nichts Verwertbares drinsteht (z.B. '3 Locations')."""
    text = (location or "").strip()
    if not text or re.fullmatch(r"\d+\s+(locations?|standorte)", text, re.IGNORECASE):
        return None
    return bool(_SWISS.search(text))


class JobFilter:
    """Ein Job passt, wenn ALLE Wörter mindestens eines Suchbegriffs im Titel vorkommen
    ("Data Engineer" passt auf "Senior Data Engineer (m/w/d)") und – falls swiss_only –
    der Ort nicht eindeutig ausserhalb der Schweiz liegt. Leere Titelliste = alle Titel."""

    def __init__(self, titles: list[str], swiss_only: bool = True):
        self.titles = [t.strip() for t in titles if t.strip()]
        self.swiss_only = swiss_only
        self._terms = [re.findall(r"\w+", t.lower()) for t in self.titles]

    def title_ok(self, title: str) -> bool:
        if not self._terms:
            return bool(title.strip())
        low = title.lower()
        return any(all(w in low for w in term) for term in self._terms)

    def location_ok(self, location: str) -> bool:
        return not self.swiss_only or is_swiss(location) is not False

    def __call__(self, title: str, location: str = "") -> bool:
        return self.title_ok(title) and self.location_ok(location)
