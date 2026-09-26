from __future__ import annotations

import io

from pypdf import PdfReader


def pdf_to_text(data: bytes) -> str:
    """Text aus einem PDF. Gescannte PDFs (nur Bilder) enthalten keinen Text –
    dann bitte das CV als 'echtes' PDF aus Word/Google Docs exportieren."""
    reader = PdfReader(io.BytesIO(data))
    return "\n".join(page.extract_text() or "" for page in reader.pages).strip()
