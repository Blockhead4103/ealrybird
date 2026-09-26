# 🔎 JobScout Schweiz

Durchsucht die Karriereseiten von Schweizer Firmen (≥ 100 Mitarbeitende), filtert nach Jobtitel und Alter,
zeigt die **Must-Have-Skills** jeder Stelle, gleicht sie mit deinem **CV (PDF)** ab und schickt dir die
besten Treffer per **E-Mail**.

**Kosten: 0 Franken.** Läuft auf deinem eigenen Computer, ohne Abo und ohne kostenpflichtige KI.

---

## Was du wissen solltest (ehrlich)

| Thema | So funktioniert es | Grenze |
|---|---|---|
| Firmenliste | `companies.yaml` enthält eine Startliste mit 20 Firmen (Novartis, Roche, Swisscom, On …). Weitere per Klick in der App oder per JSON-Import. | Die Kennungen der Startliste sind nicht live geprüft. Die Mitarbeiterzahl ist optional: Fehlt sie, wird die Firma immer durchsucht. |
| Nur Schweiz | Globale Firmen (z.B. Novartis, Takeda) haben tausende Stellen weltweit. Standardmässig werden nur Stellen mit Schweizer Ort behalten (Ländername oder eine von ~100 Schweizer Ortschaften). | Stellen ohne verwertbare Ortsangabe (z.B. "3 Locations") bleiben drin. Ein Ort wie "Baden" wird als Schweiz gewertet, auch wenn Baden-Baden gemeint wäre. |
| Stellen lesen | Viele grosse Firmen nutzen ein Bewerbersystem mit öffentlicher Schnittstelle: **SmartRecruiters, Greenhouse, Lever, Personio, Recruitee, Workday**. Für alle anderen gibt es einen allgemeinen Modus (liest schema.org-Stellendaten). | Seiten, die ihre Stellen nur per JavaScript nachladen (z.B. viele SAP-SuccessFactors-Seiten), liefern im allgemeinen Modus oft **nichts**. Die Workday-Schnittstelle ist inoffiziell und kann sich ändern. |
| Must-Have-Skills | Gratis-Regeln: Abschnitt "Ihr Profil / Anforderungen" finden und **Zeile für Zeile** auswerten: bekannte Skills (125 Einträge, v.a. DE/EN), **Studienrichtungen** (19, z.B. Recht, BWL, Informatik – nur in Zeilen, die von Ausbildung sprechen), "oder"-Aufzählungen als Alternativen, "von Vorteil" = Nice-to-have. | Zeilen ohne erkannten Skill (z.B. "Strong organizational skills") werden als **"selbst prüfen"** angezeigt, nicht bewertet. "Or a related discipline" kann das Tool nicht beurteilen. |
| "Nicht älter als" | Nutzt das Veröffentlichungsdatum der Stelle. | Fehlt es, zählt das Datum, an dem JobScout die Stelle **zum ersten Mal gesehen** hat. |
| Match-Wert | 60 % erfüllte **fachliche** Anforderungen (z.B. Verkauf, Python, Laborautomation, Studienrichtung) · 10 % **Basis**-Anforderungen (Sprachen, Excel, "irgendein Abschluss", Führerausweis) · 15 % Nice-to-haves · 15 % Wörter aus dem Jobtitel im CV. Keine fachliche Anforderung erfüllt → höchstens 30 %. Fehlende verlangte **Studienrichtung/Doktorat** → ⚠️ Ausschlusskriterium, höchstens 40 %, ans Ende der Liste. "Oder vergleichbar" im Inserat → verwandte Studienrichtungen zählen (z.B. Wirtschaftsinformatik für Informatik). Standard: nur Stellen ab **50 %** werden angezeigt und gemailt. | Eine grobe Schätzung – das Inserat bitte trotzdem selbst lesen. Die Gewichte sind von Hand gewählt, nicht wissenschaftlich ermittelt. |
| Studierende, Praktika, Lehrstellen, Doktorat | Werden standardmässig **ausgeblendet** (erkannt am Titel, z.B. "Intern", "Werkstudent", "Lernende", oder an Sätzen wie "enrolled in a Bachelor's program"). Häkchen in der App bzw. `--mit-studentenjobs` zeigt sie. | Stellen, die sich nur indirekt an Studierende richten, können durchrutschen. |

> **Stand der Prüfung:** Alle Teile sind mit simulierten Antworten der Anbieter und mit einer lokalen Test-Karriereseite
> automatisch getestet (46 Tests). Gegen die echten Anbieter-Server konnte beim Erstellen **nicht** live getestet werden.
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
5. **Fachfremde Stellen?** Immer Jobtitel angeben (ohne Titel wird *alles* durchsucht). Zusätzlich im Feld
   *"Titel ausschliessen"* Wortteile eintragen, z.B. `Elektr, Verkauf, Pflege` (CLI: `--ohne "..."`).
   Verlangt ein Inserat einen bestimmten **Lehrberuf** (z.B. "Lehre als Elektroinstallateur EFZ") und steht dieser
   Beruf nicht in deinem CV, wird die Stelle mit ⚠️ markiert und auf höchstens 40 % begrenzt.
6. **Skill-Liste hochladen (optional):** `.txt` (eine Skill pro Zeile oder mit Komma) oder `.csv` (Spalte `Name` oder
   `Skill`). Sie wird zusammen mit dem CV ausgewertet (CLI: `--skills-datei datei.csv`).
7. **Stimmt ein "Fehlt" nicht?** Öffne *"Was JobScout in deinem CV erkannt hat"*. Dort siehst du die erkannten Skills und
   den Text, den das Tool aus deinem PDF lesen konnte. Fehlt etwas, trage es im Feld *"Zusätzlich im CV nicht erkannt,
   aber vorhanden"* ein (z.B. `Führungserfahrung, Projektmanagement`). Kommandozeile: `--zusatz-skills "..."`.

   Im CV erkennt JobScout auch typische Formulierungen statt nur Stichworte, z.B. "Teamleiter", "Head of …",
   "6 direct reports", "Leitung eines Teams von 8 Personen" → Führungserfahrung; "Projektleiter" → Projektmanagement;
   "Schnittstelle zur Geschäftsleitung" → Stakeholder Management.

### Viele Firmen auf einmal importieren
JSON-Datei im Format `[{"name": "...", "ats": "workday", "url": "https://x.wd3.myworkdayjobs.com", "site": "Careers"}, {"name": "...", "ats": "greenhouse", "token": "..."}]`, dann:
```
python import_companies.py meine_firmen.json
```
Bereits vorhandene Firmennamen werden übersprungen.

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

---

## Online stellen (gratis, Streamlit Community Cloud)

**Warum nicht Vercel?** Vercel führt Python nur als kurzlebige "Serverless Functions" aus. Eine Streamlit-App braucht
aber einen dauerhaft laufenden Server mit stehender Verbindung zum Browser (WebSocket), und das Scrapen dauert länger
als die Zeitlimits solcher Funktionen. Ausserdem wäre das Dateisystem dort schreibgeschützt. Streamlit Community Cloud
ist genau für solche Apps gemacht. (Stand der Anbieter-Angebote bitte selbst prüfen, sie ändern sich.)

1. Auf <https://share.streamlit.io> mit GitHub anmelden → **Create app** → Repository `ealrybird`, Branch wählen,
   Hauptdatei `app.py`.
2. Unter **Advanced settings → Secrets** den Inhalt von `.streamlit/secrets.toml.example` einfügen und ausfüllen.
   **Unbedingt `APP_PASSWORD` und `ALLOWED_EMAILS` setzen**, sonst kann jeder mit dem Link die App benutzen und
   über dein E-Mail-Konto Mails verschicken.
3. **Deploy** klicken. Nach ein paar Minuten bekommst du eine Adresse wie `https://….streamlit.app`.

Das musst du online beachten:
- **Firmen dauerhaft speichern:** In der App hinzugefügte Firmen gehen bei jedem Neustart verloren. Die App zeigt dir
  nach dem Hinzufügen den Eintrag an: Kopiere ihn auf GitHub in `companies.yaml` (Datei öffnen → Stift-Symbol →
  einfügen → *Commit changes*). Die App aktualisiert sich danach automatisch.
- **Datum "zuerst gesehen"** wird online ebenfalls bei jedem Neustart zurückgesetzt.
- **Dein CV** wird zur Verarbeitung auf die Server von Streamlit hochgeladen. JobScout speichert es nicht,
  es liegt aber während der Sitzung dort im Arbeitsspeicher.
- **Täglicher Automatik-Versand** läuft online nicht, weil die Gratis-App nach einer Weile ohne Besuch schlafen geht.
  Dafür die lokale Variante oben nutzen.

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
cli.py                  Kommandozeile / täglicher Versand (--weltweit = auch Stellen ausserhalb CH)
import_companies.py     Firmenliste aus JSON importieren
companies.yaml          Firmenliste
jobscout/
  config.py             .env, Firmenliste laden/ergänzen
  models.py             Company, Job, Match
  scrapers/
    http.py             höfliches HTTP (robots.txt, Pausen, Encoding)
    ats.py              SmartRecruiters, Greenhouse, Lever, Personio, Recruitee, Workday
    jsonld.py           allgemeiner Modus (schema.org/JobPosting)
    __init__.py         Titel-Filter, paralleles Scrapen
  scrapers/filters.py   Titel- und Schweiz-Filter
  detect.py             erkennt das Bewerbersystem hinter einer URL
  importer.py           JSON-Firmenliste -> companies.yaml
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
