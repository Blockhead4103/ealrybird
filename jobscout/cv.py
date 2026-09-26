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
