"""Merkt sich, wann eine Stelle zum ersten Mal gesehen wurde (SQLite-Datei in data/).

Nötig, weil nicht jede Karriereseite ein Veröffentlichungsdatum angibt: Für den Filter
"nicht älter als X Tage" wird dann das Datum des ersten Funds verwendet.
"""
from __future__ import annotations

import sqlite3
from datetime import date
from pathlib import Path

from .config import DATA_DIR
from .models import Job


def _connect(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.execute("CREATE TABLE IF NOT EXISTS seen (key TEXT PRIMARY KEY, first_seen TEXT NOT NULL)")
    return conn


def stamp_first_seen(jobs: list[Job], path: Path = DATA_DIR / "jobs.sqlite", today: date | None = None) -> None:
    today = today or date.today()
    with _connect(path) as conn:
        for job in jobs:
            conn.execute("INSERT OR IGNORE INTO seen (key, first_seen) VALUES (?, ?)", (job.key, today.isoformat()))
            row = conn.execute("SELECT first_seen FROM seen WHERE key = ?", (job.key,)).fetchone()
            job.first_seen = date.fromisoformat(row[0])
