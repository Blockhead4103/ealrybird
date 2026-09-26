"""Firmenliste aus einer JSON-Datei in companies.yaml übernehmen.

  python import_companies.py meine_firmen.json
"""
import sys

from jobscout.importer import import_json

if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    added, skipped = import_json(sys.argv[1])
    print(f"{len(added)} Firmen hinzugefügt: {', '.join(added)}")
    for msg in skipped:
        print("übersprungen –", msg)
