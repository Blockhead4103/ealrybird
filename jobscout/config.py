from __future__ import annotations

import os
from pathlib import Path

import yaml

from .models import Company

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"

try:  # .env ist optional
    from dotenv import load_dotenv

    load_dotenv(ROOT / ".env")
except ImportError:  # pragma: no cover
    pass

SUPPORTED_SOURCES = {"smartrecruiters", "greenhouse", "lever", "personio", "recruitee", "workday", "jsonld"}


def env(name: str, default: str = "") -> str:
    """Liest zuerst Umgebungsvariablen/.env, dann Streamlit-Secrets (für Streamlit Cloud)."""
    value = os.getenv(name)
    if value:
        return value
    try:
        import streamlit as st

        if name in st.secrets:
            return str(st.secrets[name])
    except Exception:
        pass
    return default


def load_companies(path: Path | str = ROOT / "companies.yaml", min_employees: int = 100) -> list[Company]:
    raw = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
    companies = []
    for entry in raw.get("companies", []):
        source = str(entry.get("source", "")).lower()
        if source not in SUPPORTED_SOURCES:
            raise ValueError(f"{entry.get('name')}: unbekannte Quelle '{source}'. Erlaubt: {sorted(SUPPORTED_SOURCES)}")
        employees = int(entry.get("employees", 0))
        if employees < min_employees:
            continue
        companies.append(
            Company(
                name=entry["name"],
                employees=employees,
                source=source,
                target=str(entry["target"]),
                extra={k: v for k, v in entry.items() if k not in {"name", "employees", "source", "target"}},
            )
        )
    return companies


def add_company(entry: dict, path: Path | str = ROOT / "companies.yaml") -> None:
    """Hängt einen Eintrag an companies.yaml an, ohne die Kommentare zu verlieren."""
    path = Path(path)
    text = path.read_text(encoding="utf-8") if path.exists() else "companies:\n"
    existing = yaml.safe_load(text) or {}
    if any(c.get("name") == entry["name"] for c in existing.get("companies") or []):
        raise ValueError(f"'{entry['name']}' ist bereits in der Liste.")
    text = text.replace("companies: []", "companies:")
    if "companies:" not in text:
        text += "\ncompanies:\n"
    block = yaml.safe_dump([entry], allow_unicode=True, sort_keys=False)
    text = text.rstrip("\n") + "\n" + "".join("  " + line + "\n" for line in block.splitlines())
    path.write_text(text, encoding="utf-8")
