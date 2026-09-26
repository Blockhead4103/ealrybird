# 🔎 JobScout Schweiz

Durchsucht die Karriereseiten von Schweizer Firmen (≥ 100 Mitarbeitende), filtert nach Jobtitel und Alter,
zeigt die **Must-Have-Skills** jeder Stelle, gleicht sie mit deinem **CV (PDF)** ab und schickt dir die
besten Treffer per **E-Mail**.

**Kosten: 0 Franken.** Läuft auf deinem eigenen Computer, ohne Abo und ohne kostenpflichtige KI.

---

## Was du wissen solltest (ehrlich)

| Thema | So funktioniert es | Grenze |
|---|---|---|
| Firmenliste | Du pflegst sie selbst in `companies.yaml` (in der App per Klick). | Es gibt keine kostenlose, offizielle Liste "alle CH-Firmen > 100 MA" mit Karriere-URLs. Die Mitarbeiterzahl trägst du selbst ein (z.B. aus dem Geschäftsbericht). |
| Stellen lesen | Viele grosse Firmen nutzen ein Bewerbersystem mit öffentlicher Schnittstelle: **SmartRecruiters, Greenhouse, Lever, Personio, Recruitee, Workday**. Für alle anderen gibt es einen allgemeinen Modus (liest schema.org-Stellendaten). | Seiten, die ihre Stellen nur per JavaScript nachladen (z.B. viele SAP-SuccessFactors-Seiten), liefern im allgemeinen Modus oft **nichts**. Die Workday-Schnittstelle ist inoffiziell und kann sich ändern. |
| Must-Have-Skills | Gratis-Regeln: Abschnitt "Ihr Profil / Anforderungen" finden, "von Vorteil" = Nice-to-have, bekannte Skills aus einem Wörterbuch (118 Einträge, v.a. DE/EN) erkennen. | Skills, die nicht im Wörterbuch stehen, werden nicht erkannt → eigene ergänzen (siehe unten) oder optional KI nutzen. |
| "Nicht älter als" | Nutzt das Veröffentlichungsdatum der Stelle. | Fehlt es, zählt das Datum, an dem JobScout die Stelle **zum ersten Mal gesehen** hat. |
| Match-Wert | 70 % Must-Haves im CV · 20 % Nice-to-haves · 10 % Wörter aus dem Jobtitel im CV. | Eine grobe Schätzung – das Inserat bitte trotzdem selbst lesen. |

> **Stand der Prüfung:** Alle Teile sind mit simulierten Antworten der Anbieter und mit einer lokalen Test-Karriereseite
> automatisch getestet (21 Tests). Gegen die echten Anbieter-Server konnte beim Erstellen **nicht** live getestet werden.
> Falls eine Quelle einen Fehler meldet, siehst du ihn in der App pro Firma.

---

## Installation (einmalig, ca. 10 Minuten)

### 1. Python installieren
- **Windows:** <https://www.python.org/downloads/> → Installer starten → **Häkchen bei "Add python.exe to PATH" setzen**.
- **Mac:** <https://www.python.org/downloads/> → Installer starten.

Prüfen: Terminal öffnen (Windows: Startmenü → "cmd"; Mac: Programme → Dienstprogramme → Terminal) und eingeben:
```
python --version
```
(Auf dem Mac ggf. `python3` statt `python` verwenden – auch in allen Befehlen unten.)

### 2. JobScout herunterladen
Auf GitHub: grüner Knopf **Code → Download ZIP**, entpacken, z.B. nach `Dokumente/jobscout`.

### 3. Im Terminal in den Ordner wechseln und einrichten
```
cd Dokumente/jobscout
python -m venv .venv
```
Aktivieren – **Windows:** `.venv\Scripts\activate`   **Mac:** `source .venv/bin/activate`
```
pip install -r requirements.txt
```

### 4. E-Mail einrichten (für den Versand)
1. Datei `.env.example` kopieren und die Kopie `.env` nennen.
2. Mit einem Texteditor öffnen und deine Daten eintragen.

**Gmail (gratis):** Du brauchst ein *App-Passwort* (nicht dein normales Passwort):
Google-Konto → Sicherheit → 2-Schritt-Verifizierung einschalten → "App-Passwörter" → eines erstellen → den
16-stelligen Code bei `SMTP_PASSWORD` eintragen. (Google ändert Menüs gelegentlich – falls der Weg abweicht,
in der Google-Hilfe nach "App-Passwort" suchen.)

Andere Anbieter funktionieren auch; Server und Port findest du in deren Hilfe (Stichwort "SMTP").

### 5. Starten
```
streamlit run app.py
```
Der Browser öffnet sich mit der App. Beenden: im Terminal `Ctrl + C`.

Beim nächsten Mal nur: Terminal → `cd Dokumente/jobscout` → aktivieren (Schritt 3) → `streamlit run app.py`.

---

## Benutzung

1. **Reiter "Firma hinzufügen":** URL der Karriereseite einfügen → *Erkennen* → Name + Mitarbeiterzahl eingeben → *Hinzufügen*.
   Tipp: Wenn "allgemeiner Modus" erscheint, auf der Karriereseite auf eine einzelne Stelle klicken und **deren** URL
   probieren – oft verrät die das Bewerbersystem.
2. **Reiter "Suche":** Jobtitel (z.B. `Data Engineer, Business Analyst`), "Nicht älter als" in Tagen, CV hochladen → *Suchen*.
3. Ergebnis: Stellen sortiert nach Match, mit Must-Have-Skills, was du hast und was dir fehlt.
4. E-Mail-Adresse eingeben → *Top-Treffer per E-Mail senden*.

### Eigene Skills ergänzen
Datei `data/extra_skills.txt` anlegen (Ordner `data` ggf. erstellen), eine Zeile pro Skill:
```
Kubernetes-Operatoren: operator sdk, kubebuilder
Pflegeprozess: pflegeprozess, pflegediagnostik
```
Links vom Doppelpunkt der Anzeigename, rechts Suchbegriffe (klein geschrieben).

---

## Automatisch jeden Morgen eine E-Mail (optional, gratis)

Die Kommandozeilen-Version macht alles in einem Schritt:
```
python cli.py --titles "Data Engineer, Data Analyst" --days 2 --cv MeinCV.pdf --email du@example.ch --min-score 40
```

- **Windows:** "Aufgabenplanung" öffnen → *Einfache Aufgabe erstellen* → täglich → Programm:
  `C:\Pfad\zu\jobscout\.venv\Scripts\python.exe`, Argumente: `cli.py --titles "..." --days 2 --cv MeinCV.pdf --email ...`,
  "Starten in": `C:\Pfad\zu\jobscout`.
- **Mac:** Im Terminal `crontab -e` und eine Zeile einfügen (täglich 7:00):
  `0 7 * * * cd /Users/DEINNAME/Documents/jobscout && .venv/bin/python cli.py --titles "..." --days 2 --cv MeinCV.pdf --email ...`

Der Computer muss zu dieser Zeit eingeschaltet sein.

> **Warum nicht einfach online (Streamlit Cloud)?** Geht grundsätzlich gratis, aber: (1) jeder mit dem Link könnte über
> dein E-Mail-Konto Mails auslösen, (2) dort hinzugefügte Firmen gehen beim Neustart verloren, (3) dein CV läge auf
> fremden Servern. Für den Privatgebrauch ist lokal einfacher und sicherer.

---

## Optional: KI für bessere Skill-Erkennung

Standardmässig nicht nötig. Wenn du willst, trage in `.env` einen Anbieter mit *OpenAI-kompatibler* Schnittstelle ein:

- **Ollama (komplett gratis, lokal):** <https://ollama.com> installieren, z.B. `ollama pull llama3.1`, dann
  `LLM_BASE_URL=http://localhost:11434/v1` und `LLM_MODEL=llama3.1`. Braucht einen einigermassen starken PC.
- **Cloud-Anbieter mit Gratis-Kontingent** (z.B. Groq): Konditionen und Modellnamen ändern sich – bitte aktuell auf deren
  Webseite prüfen. Beachte: Die Stellentexte (nicht dein CV) werden dann an diesen Anbieter geschickt.

Danach in der App das Häkchen "KI für Skill-Erkennung nutzen" setzen (CLI: `--llm`). Fällt die KI aus, nutzt
JobScout automatisch wieder die Gratis-Regeln.

---

## Fair & rechtlich

- JobScout respektiert `robots.txt`, wartet 1 Sekunde zwischen Anfragen pro Server und lädt höchstens 60 Stellen-Details pro Firma.
- Nutze es für deine **private** Stellensuche. Die Daten nicht weiterverkaufen oder veröffentlichen.
- Die Nutzungsbedingungen einzelner Webseiten können Scraping einschränken. Das ist keine Rechtsberatung – im Zweifel die
  AGB der jeweiligen Seite lesen.

---

## Für Entwickler

**Tech-Stack:** Python 3.10+, `requests` + `BeautifulSoup` (Scraping, bewusst ohne Selenium – leichter und schneller;
für JS-Seiten werden stattdessen die JSON-Schnittstellen der Bewerbersysteme genutzt), `pypdf` (CV), Streamlit (UI),
SQLite (Datum des ersten Funds), `smtplib` (E-Mail), optional LLM über OpenAI-kompatibles `/chat/completions`.

```
app.py                  Streamlit-Oberfläche
cli.py                  Kommandozeile / täglicher Versand
companies.yaml          Firmenliste
jobscout/
  config.py             .env, Firmenliste laden/ergänzen
  models.py             Company, Job, Match
  scrapers/
    http.py             höfliches HTTP (robots.txt, Pausen, Encoding)
    ats.py              SmartRecruiters, Greenhouse, Lever, Personio, Recruitee, Workday
    jsonld.py           allgemeiner Modus (schema.org/JobPosting)
    __init__.py         Titel-Filter, paralleles Scrapen
  detect.py             erkennt das Bewerbersystem hinter einer URL
  skills.py             Must-Have/Nice-to-have-Erkennung (Regeln + optional LLM)
  cv.py                 PDF → Text
  matcher.py            Scoring
  storage.py            "zuerst gesehen"-Datum (data/jobs.sqlite)
  emailer.py            HTML-E-Mail + SMTP
  pipeline.py           Gesamtablauf
tests/                  pytest, alle HTTP-Antworten simuliert
```

Tests: `pip install pytest && python -m pytest`

Neue Quelle hinzufügen: Funktion `(company, wanted) -> list[Job]` in `jobscout/scrapers/` schreiben, in `SCRAPERS`
eintragen und in `config.SUPPORTED_SOURCES` ergänzen.
