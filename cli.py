"""Kommandozeile – z.B. für den automatischen täglichen Versand.

Beispiel:
  python cli.py --titles "Data Engineer, Data Analyst" --days 14 --cv MeinCV.pdf --email du@example.ch
"""
from __future__ import annotations

import argparse
import logging
from pathlib import Path

from jobscout.cv import pdf_to_text
from jobscout.emailer import build_email, send
from jobscout.pipeline import find_jobs, match_cv


def main() -> None:
    parser = argparse.ArgumentParser(description="JobScout Schweiz")
    parser.add_argument("--titles", default="", help="Jobtitel, mit Komma getrennt")
    parser.add_argument("--days", type=int, default=14, help="nicht älter als X Tage")
    parser.add_argument("--cv", type=Path, help="CV als PDF")
    parser.add_argument("--email", help="Empfänger-Adresse (ohne = nur Ausgabe)")
    parser.add_argument("--top", type=int, default=15)
    parser.add_argument("--min-score", type=float, default=0)
    parser.add_argument("--min-employees", type=int, default=100)
    parser.add_argument("--weltweit", action="store_true", help="auch Stellen ausserhalb der Schweiz")
    parser.add_argument("--llm", action="store_true", help="KI zur Skill-Erkennung nutzen (siehe .env)")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(message)s")

    titles = [t.strip() for t in args.titles.split(",") if t.strip()]
    jobs, errors = find_jobs(titles, args.days, use_llm=args.llm, min_employees=args.min_employees, progress=print,
                              swiss_only=not args.weltweit)
    print(f"\n{len(jobs)} Stellen gefunden, {len(errors)} Quellen mit Fehlern.\n")

    if not args.cv:
        for j in jobs:
            print(f"- {j.title} | {j.company} | {j.effective_date} | Must-Have: {', '.join(j.must_have)}\n  {j.url}")
        return

    matches = match_cv(jobs, pdf_to_text(args.cv.read_bytes()), min_score=args.min_score, top=args.top)
    for m in matches:
        print(f"{m.score:5.1f}%  {m.job.title} | {m.job.company}\n        fehlt: {', '.join(m.missing) or '–'}\n        {m.job.url}")
    if args.email and matches:
        send(build_email(matches, args.email, titles, args.days))
        print(f"\nE-Mail an {args.email} gesendet.")
    elif args.email:
        print("\nKeine Treffer – keine E-Mail gesendet.")


if __name__ == "__main__":
    main()
