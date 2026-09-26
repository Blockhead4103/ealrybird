from __future__ import annotations

import io
import re
import unicodedata

from pypdf import PdfReader


def clean_text(text: str) -> str:
    # NFKC: zerlegte Umlaute ("u" + "¨") und Ligaturen ("ﬁ") zusammenführen
    text = unicodedata.normalize("NFKC", text or "")
    # Silbentrennung am Zeilenende aufheben: "Projekt-\nleiter" -> "Projektleiter"
    text = re.sub(r"(\w)-\n\s*([a-zäöüéèà])", r"\1\2", text)
    return text.strip()


def pdf_to_text(data: bytes) -> str:
    """Text aus einem PDF. Gescannte PDFs (nur Bilder) enthalten keinen Text –
    dann bitte das CV als 'echtes' PDF aus Word/Google Docs exportieren."""
    reader = PdfReader(io.BytesIO(data))
    return clean_text("\n".join(page.extract_text() or "" for page in reader.pages))


def skills_file_to_text(data: bytes, filename: str = "") -> str:
    """Skill-Liste aus .txt (eine Zeile oder Komma-getrennt) oder .csv.
    Bei CSV mit Kopfzeile wird die Spalte "Name"/"Skill"/"Skills" genommen (z.B. ein Skills-Export
    aus LinkedIn – dessen Spaltenname bitte selbst prüfen), sonst alle Zellen."""
    import csv

    text = data.decode("utf-8-sig", errors="replace")
    if filename.lower().endswith(".csv"):
        rows = list(csv.reader(io.StringIO(text)))
        if rows:
            header = [h.strip().lower() for h in rows[0]]
            for col in ("name", "skill", "skills", "fähigkeit", "kompetenz"):
                if col in header:
                    i = header.index(col)
                    return "\n".join(r[i].strip() for r in rows[1:] if len(r) > i and r[i].strip())
        return "\n".join(cell.strip() for r in rows for cell in r if cell.strip())
    return "\n".join(part.strip() for part in re.split(r"[,;\n]", text) if part.strip())
