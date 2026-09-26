"""Importiert eine Firmenliste im JSON-Format in companies.yaml.

Erwartetes Format (Liste von Objekten):
  {"name": "...", "ats": "workday", "url": "https://x.wd3.myworkdayjobs.com", "site": "Careers", ...}
  {"name": "...", "ats": "smartrecruiters" | "greenhouse" | "lever" | "personio" | "recruitee", "token": "..."}
  {"name": "...", "ats": "jsonld", "url": "https://firma.ch/karriere"}
Optional: "employees", "hq", "startup". Unbekannte Felder werden ignoriert.
"""
from __future__ import annotations

import json
from pathlib import Path

from .config import ROOT, SUPPORTED_SOURCES, add_company


def to_entry(item: dict) -> dict:
    source = str(item.get("ats", "")).lower()
    if source not in SUPPORTED_SOURCES:
        raise ValueError(f"{item.get('name')}: ATS '{source}' wird nicht unterstützt")
    if source == "workday":
        base = str(item["url"]).rstrip("/")
        target = f"{base}/{item['site']}" if item.get("site") and not base.endswith(item["site"]) else base
    elif source == "jsonld":
        target = item["url"]
    else:
        target = item["token"]
    entry: dict = {"name": item["name"]}
    if item.get("employees") not in (None, ""):
        entry["employees"] = int(item["employees"])
    entry.update({"source": source, "target": target})
    if item.get("hq"):
        entry["hq"] = item["hq"]
    if item.get("startup"):
        entry["startup"] = True
    return entry


def import_json(json_path: Path | str, yaml_path: Path | str = ROOT / "companies.yaml") -> tuple[list[str], list[str]]:
    """Gibt (importierte Namen, übersprungene Meldungen) zurück. Bereits vorhandene Namen werden übersprungen."""
    added, skipped = [], []
    for item in json.loads(Path(json_path).read_text(encoding="utf-8")):
        try:
            add_company(to_entry(item), yaml_path)
            added.append(item["name"])
        except (ValueError, KeyError) as exc:
            skipped.append(f"{item.get('name', '?')}: {exc}")
    return added, skipped
