"""Erkennt Must-Have- und Nice-to-have-Skills in Stellenbeschreibungen.

Standard (gratis, offline): Regeln + Skill-Wörterbuch.
  1. Den Anforderungs-Abschnitt finden ("Ihr Profil", "Requirements", "Votre profil" …).
  2. Zeilen mit "von Vorteil", "nice to have", "wünschenswert" … gelten als Nice-to-have.
  3. In den übrigen Zeilen werden bekannte Skills aus SKILLS gesucht.
Optional: ein Sprachmodell (LLM) über eine OpenAI-kompatible Schnittstelle (siehe .env.example).

Das Wörterbuch ist bewusst erweiterbar: eigene Skills einfach in SKILLS ergänzen
oder in data/extra_skills.txt eine Zeile pro Skill eintragen ("Name: alias1, alias2").
"""
from __future__ import annotations

import json
import logging
import re
from functools import lru_cache

import requests

from .config import DATA_DIR, env
from .models import Job, Requirement

log = logging.getLogger(__name__)

# Anzeigename -> Suchbegriffe (klein geschrieben). Wortgrenzen werden automatisch beachtet.
SKILLS: dict[str, list[str]] = {
    # Programmiersprachen
    "Python": ["python"], "Java": ["java"], "JavaScript": ["javascript", "js"], "TypeScript": ["typescript"],
    "C#": ["c#", ".net", "dotnet"], "C++": ["c++"], "Go": ["golang"], "Rust": ["rust"], "Kotlin": ["kotlin"],
    "Swift": ["swift"], "PHP": ["php"], "Ruby": ["ruby"], "Scala": ["scala"], "R": ["r-studio", "rstudio", "programmiersprache r"],
    "SQL": ["sql", "t-sql", "pl/sql"], "Bash": ["bash", "shell scripting"], "ABAP": ["abap"], "MATLAB": ["matlab"],
    # Web / Frameworks
    "React": ["react", "react.js"], "Angular": ["angular"], "Vue": ["vue", "vue.js"], "Node.js": ["node.js", "nodejs"],
    "Spring": ["spring boot", "spring"], "Django": ["django"], "FastAPI": ["fastapi"], "Flask": ["flask"],
    "REST APIs": ["restful", "rest-api", "rest api", "rest apis"], "GraphQL": ["graphql"], "HTML/CSS": ["html", "css"],
    # Daten / KI
    "Machine Learning": ["machine learning", "maschinelles lernen", "ml"], "Deep Learning": ["deep learning"],
    "NLP": ["nlp", "natural language processing"], "LLMs / GenAI": ["llm", "llms", "generative ai", "genai"],
    "PyTorch": ["pytorch"], "TensorFlow": ["tensorflow"], "scikit-learn": ["scikit-learn", "sklearn"],
    "Pandas": ["pandas"], "Spark": ["spark", "pyspark"], "Databricks": ["databricks"], "Snowflake": ["snowflake"],
    "dbt": ["dbt"], "Airflow": ["airflow"], "Kafka": ["kafka"], "ETL": ["etl", "elt", "data pipelines", "datenpipelines"],
    "Data Warehouse": ["data warehouse", "dwh"], "Power BI": ["power bi", "powerbi"], "Tableau": ["tableau"],
    "Qlik": ["qlik"], "Excel": ["excel"], "Statistik": ["statistik", "statistics", "statistical"],
    "PostgreSQL": ["postgresql", "postgres"], "MySQL": ["mysql"], "Oracle": ["oracle"], "MongoDB": ["mongodb"],
    # Cloud / DevOps
    "AWS": ["aws", "amazon web services"], "Azure": ["azure"], "GCP": ["gcp", "google cloud"],
    "Docker": ["docker"], "Kubernetes": ["kubernetes", "k8s", "openshift"], "Terraform": ["terraform"],
    "Ansible": ["ansible"], "CI/CD": ["ci/cd", "cicd", "jenkins", "gitlab ci", "github actions"], "Git": ["git"],
    "Linux": ["linux", "unix"], "Windows Server": ["windows server"], "Networking": ["tcp/ip", "netzwerk", "networking"],
    "IT Security": ["cyber security", "cybersecurity", "it-security", "it security", "informationssicherheit", "iso 27001"],
    "Microservices": ["microservices", "microservice"],
    # Enterprise
    "SAP": ["sap", "s/4hana", "s4hana"], "Salesforce": ["salesforce"], "ServiceNow": ["servicenow"],
    "Dynamics 365": ["dynamics 365", "microsoft dynamics"], "Jira": ["jira"], "Confluence": ["confluence"],
    # Methoden / Rollen
    "Scrum / Agile": ["scrum", "agile", "agil", "kanban", "scaled agile"], "Projektmanagement": ["projektmanagement", "project management", "projektleitung"],
    "PMP / Prince2": ["pmp", "prince2", "hermes"], "ITIL": ["itil"], "Requirements Engineering": ["requirements engineering", "anforderungsmanagement", "business analysis"],
    "UX/UI Design": ["ux", "ui design", "user experience", "figma"], "Testautomatisierung": ["testautomatisierung", "test automation", "selenium", "cypress"],
    "Führungserfahrung": ["führungserfahrung", "leadership", "people management", "führung von teams", "teamleitung"],
    "Stakeholder Management": ["stakeholder management", "stakeholdermanagement", "stakeholder"],
    "Change Management": ["change management", "change-management"], "Lean / Six Sigma": ["lean", "six sigma"],
    # Finanzen / Wirtschaft
    "Rechnungswesen": ["rechnungswesen", "buchhaltung", "accounting"], "Controlling": ["controlling", "controller"],
    "IFRS": ["ifrs"], "Swiss GAAP FER": ["swiss gaap", "gaap fer"], "Treuhand": ["treuhand", "fachausweis treuhand"],
    "Steuern": ["steuern", "tax", "mwst", "mehrwertsteuer"], "Risk Management": ["risk management", "risikomanagement"],
    "Compliance": ["compliance", "aml", "kyc", "finma"],
    "Gesellschaftsrecht": ["corporate law", "company law", "gesellschaftsrecht", "aktienrecht", "obligationenrecht", "droit des sociétés"],
    "Corporate Governance": ["corporate governance", "governance framework", "governance frameworks"],
    "Company Secretary": ["company secretarial", "company secretary", "corporate secretary", "board secretary", "verwaltungsratssekretariat", "vr-sekretariat"],
    "Vertragsrecht / Verträge": ["contract law", "vertragsrecht", "contract management", "vertragsmanagement", "contract drafting"],
    "Rechtsberatung / Legal": ["legal advice", "rechtsberatung", "legal counsel", "litigation", "prozessführung", "legal administration", "corporate legal"],
    "Datenschutz": ["datenschutz", "data protection", "gdpr", "dsgvo", "revdsg"],
    "Handelsregister": ["handelsregister", "commercial register", "commercial registers"], "Audit": ["audit", "revision", "wirtschaftsprüfung"],
    "Sales / Verkauf": ["verkauf", "sales", "akquisition", "business development", "key account"],
    "Marketing": ["marketing", "seo", "content marketing", "social media"], "CRM": ["crm"],
    "Einkauf / Procurement": ["einkauf", "procurement", "beschaffung"], "Supply Chain": ["supply chain", "logistik", "logistics"],
    # Technik / Ingenieurwesen / Gesundheit
    "CAD": ["cad", "autocad", "solidworks", "catia", "inventor"], "Elektrotechnik": ["elektrotechnik", "electrical engineering"],
    "Maschinenbau": ["maschinenbau", "mechanical engineering"], "Automation / SPS": ["sps", "plc", "industrial automation", "industrieautomation", "automatisierungstechnik", "siemens tia"],
    "Laborautomation": ["laboratory automation", "lab automation", "laborautomation", "laborautomatisierung", "liquid handling"],
    "Prozessautomation / RPA": ["rpa", "robotic process automation", "process automation", "prozessautomation", "prozessautomatisierung"],
    "GMP": ["gmp", "good manufacturing practice"], "Qualitätsmanagement": ["qualitätsmanagement", "quality management", "iso 9001", "qms"],
    "Regulatory Affairs": ["regulatory affairs", "mdr", "fda"], "Pflege": ["pflegefachfrau", "pflegefachmann", "pflege hf", "pflege fh"],
    "BIM": ["bim", "revit"],
    # Abschlüsse
    "Hochschulabschluss": ["bachelor", "master", "hochschulabschluss", "studium", "university degree", "fh", "eth", "uni"],
    "Doktorat / PhD": ["phd", "doktorat", "promotion", "dr."], "Eidg. Fachausweis": ["eidg. fachausweis", "eidgenössischer fachausweis", "eidg. diplom"],
    "Lehre / EFZ": ["efz", "lehre als", "berufslehre", "abgeschlossene lehre"],
    # Sprachen
    "Deutsch": ["deutsch", "german"], "Englisch": ["englisch", "english"], "Französisch": ["französisch", "french", "français"],
    "Italienisch": ["italienisch", "italian", "italiano"], "Schweizerdeutsch": ["schweizerdeutsch", "swiss german"],
    # Führerschein
    "Führerausweis": ["führerausweis", "fahrausweis", "driving licence", "driver's license"],
}

# Studienrichtungen: werden NUR in Zeilen gesucht, die von Ausbildung sprechen (siehe DEGREE_WORDS),
# damit z.B. "Swiss corporate law" in einer Erfahrungszeile nicht als Jus-Studium zählt.
DEGREE_FIELDS: dict[str, list[str]] = {
    "Studium Recht": ["law", "laws", "rechtswissenschaft", "rechtswissenschaften", "jus", "jura", "lic. iur", "lic.iur",
                      "mlaw", "blaw", "ll.m", "llm", "legal studies", "juristisch", "juristische", "droit", "giurisprudenza",
                      "anwaltspatent", "rechtsanwalt", "rechtsanwältin", "attorney at law"],
    "Studium BWL / Business": ["business administration", "betriebswirtschaft", "betriebswirtschaftslehre", "bwl", "mba",
                               "business economics", "business management", "management studies", "wirtschaftswissenschaft",
                               "wirtschaftswissenschaften", "betriebsökonomie", "betriebsökonom"],
    "Studium VWL / Economics": ["economics", "volkswirtschaft", "volkswirtschaftslehre", "vwl", "ökonomie"],
    "Studium Finance": ["finance", "finanzen", "banking", "accounting", "rechnungswesen"],
    "Studium Informatik": ["computer science", "informatik", "informatics", "software engineering"],
    "Studium Wirtschaftsinformatik": ["wirtschaftsinformatik", "business informatics", "information systems"],
    "Studium Mathematik / Statistik": ["mathematik", "mathematics", "statistik", "statistics", "data science"],
    "Studium Physik": ["physik", "physics"],
    "Studium Ingenieurwesen": ["engineering", "ingenieur", "ingenieurwesen", "ingenieurwissenschaften", "maschinenbau",
                               "maschineningenieur", "elektrotechnik", "verfahrenstechnik", "bauingenieur"],
    "Studium Chemie": ["chemistry", "chemie", "chemical engineering"],
    "Studium Biologie / Life Sciences": ["biology", "biologie", "life sciences", "life science", "biotechnology",
                                         "biotechnologie", "biochemistry", "biochemie", "molecular biology", "molekularbiologie"],
    "Studium Pharmazie": ["pharmacy", "pharmazie", "pharmaceutical sciences", "pharmaceutical science"],
    "Studium Medizin": ["medicine", "medizin", "humanmedizin"],
    "Studium Pflege": ["nursing", "pflege", "pflegewissenschaft"],
    "Studium Naturwissenschaften": ["natural sciences", "naturwissenschaften", "naturwissenschaftlich", "naturwissenschaftliches"],
    "Studium Psychologie": ["psychology", "psychologie"],
    "Studium Kommunikation": ["communications", "communication", "kommunikation", "journalism", "journalismus"],
    "Studium HR": ["human resources", "personalmanagement"],
    "Studium Architektur": ["architecture", "architektur"],
}
DEGREE_WORDS = re.compile(
    r"(?<!\w)(studium|studiengang|studienabschluss|degree|abschluss|hochschul\w*|universit\w*|bachelor|master|diplom\w*|"
    r"lizentiat|phd|doktorat|lic\.|mba|msc|bsc|ma|ba|ll\.?m|fh|eth|epfl|hsg|lehre|efz|ausbildung|education|graduate|"
    r"anwaltspatent)(?!\w)",
    re.IGNORECASE,
)
# Verwandte Studienrichtungen: zählen nur, wenn das Inserat "or related field" / "oder vergleichbar" erlaubt.
RELATED_FIELDS: list[set[str]] = [
    {"Studium Informatik", "Studium Wirtschaftsinformatik", "Studium Mathematik / Statistik", "Studium Physik",
     "Studium Ingenieurwesen"},
    {"Studium BWL / Business", "Studium VWL / Economics", "Studium Finance", "Studium Wirtschaftsinformatik"},
    {"Studium Chemie", "Studium Biologie / Life Sciences", "Studium Pharmazie", "Studium Medizin",
     "Studium Naturwissenschaften"},
]
RELATED_WORDS = re.compile(
    r"(?<!\w)(related|comparable|similar|equivalent|relevant field|vergleichbar\w*|verwandt\w*|ähnlich\w*|"
    r"gleichwertig\w*|äquivalent\w*|entsprechend\w*)(?!\w)",
    re.IGNORECASE,
)
DEGREE_LEVEL_SKILLS = {"Hochschulabschluss", "Doktorat / PhD", "Eidg. Fachausweis", "Lehre / EFZ"}
OR_WORDS = re.compile(r"(?<!\w)(or|oder|ou|o|bzw\.?|resp\.?)(?!\w)|/", re.IGNORECASE)

REQUIREMENT_HEADINGS = [
    "ihr profil", "dein profil", "ihre qualifikationen", "deine qualifikationen", "anforderungen", "anforderungsprofil",
    "was sie mitbringen", "was du mitbringst", "das bringen sie mit", "das bringst du mit", "sie bringen mit", "du bringst mit",
    "voraussetzungen", "ihre kompetenzen", "deine kompetenzen", "wen wir suchen", "what you bring", "what you'll bring",
    "your profile", "requirements", "qualifications", "who you are", "skills", "must have", "must-have",
    "what we're looking for", "what we are looking for", "about you", "votre profil", "exigences", "il tuo profilo", "requisiti",
    "essential requirements", "essential and desirable requirements", "minimum requirements", "key requirements",
    "your background", "your experience", "was sie auszeichnet", "das zeichnet sie aus", "was dich auszeichnet",
    "das zeichnet dich aus", "dein rucksack", "ihr rucksack", "fachliche anforderungen", "qualifikationen",
]
END_HEADINGS = [
    "wir bieten", "was wir bieten", "unser angebot", "deine vorteile", "ihre vorteile", "benefits", "what we offer",
    "we offer", "why join", "über uns", "about us", "kontakt", "contact", "bewerbung", "nous offrons", "ihre aufgaben",
    "deine aufgaben", "your tasks", "your responsibilities", "responsibilities", "offriamo", "why ", "warum ",
    "your key responsibilities", "commitment to diversity", "about the company", "about the team",
]
NICE_MARKERS = [
    "von vorteil", "wünschenswert", "nice to have", "nice-to-have", "ein plus", "is a plus", "a plus", "plus",
    "idealerweise", "ideally", "preferred", "bonus", "erwünscht", "vorteilhaft", "atout", "gerne gesehen", "optional",
]


def _load_extra() -> dict[str, list[str]]:
    path = DATA_DIR / "extra_skills.txt"
    extra: dict[str, list[str]] = {}
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip() or line.startswith("#"):
                continue
            name, _, aliases = line.partition(":")
            extra[name.strip()] = [a.strip().lower() for a in (aliases or name).split(",") if a.strip()]
    return extra


# Mehrzahl und deutsche Zusammensetzungen: "stakeholders", "Englischkenntnisse", "Verkaufserfahrung", "SAP-Kenntnisse"
COMPOUND = r"(?:s|es)?(?:-?(?:kenntniss\w*|kenntnis|erfahrung\w*|flair|wissen|know-how|skills?))?"


def _compile(table: dict[str, list[str]]) -> list[tuple[str, re.Pattern]]:
    compiled = []
    for name, aliases in table.items():
        alt = "|".join(re.escape(a) for a in sorted(aliases, key=len, reverse=True))
        # Wortgrenzen, die auch Sonderzeichen wie C#, C++, .NET erlauben; optionales Mehrzahl-s
        compiled.append((name, re.compile(rf"(?<![\w]){'(?:' + alt + ')'}{COMPOUND}(?![\w+#])", re.IGNORECASE)))
    return compiled


@lru_cache(maxsize=1)
def _patterns() -> list[tuple[str, re.Pattern]]:
    return _compile({**SKILLS, **_load_extra()})


@lru_cache(maxsize=1)
def _degree_patterns() -> list[tuple[str, re.Pattern]]:
    return _compile(DEGREE_FIELDS)


def _normalize(text: str) -> str:
    return (text or "").replace("\u2019", "'").replace("\u2018", "'").replace("\xa0", " ")


def find_skills(text: str) -> list[str]:
    """Alle bekannten Skills, die im Text vorkommen (Reihenfolge wie im Wörterbuch)."""
    text = _normalize(text)
    return [name for name, pattern in _patterns() if pattern.search(text)]


def find_degree_fields(line: str) -> list[str]:
    """Studienrichtungen in einer Zeile – nur wenn die Zeile von Ausbildung spricht."""
    line = _normalize(line)
    if not DEGREE_WORDS.search(line):
        return []
    return [name for name, pattern in _degree_patterns() if pattern.search(line)]


def cv_degree_fields(cv_text: str) -> list[str]:
    """Studienrichtungen im CV. Das Ausbildungswort darf auch in der Zeile davor stehen,
    weil PDF-Text oft "Master of Science" und "Informatik, ETH Zürich" auf zwei Zeilen trennt."""
    lines = _normalize(cv_text).splitlines()
    found: list[str] = []
    for i, line in enumerate(lines):
        window = " ".join(lines[max(0, i - 1) : i + 1])  # diese Zeile + die davor
        if not DEGREE_WORDS.search(window):
            continue
        for name, pattern in _degree_patterns():
            if name not in found and pattern.search(line):
                found.append(name)
    return found


def _is_heading(line: str, headings: list[str]) -> bool:
    clean = _normalize(line).lower().strip(" :#*-•\t?!")
    return len(clean) <= 60 and any(clean.startswith(h) or clean == h for h in headings)


def requirements_section(text: str) -> str:
    """Schneidet den Anforderungs-Abschnitt aus. Wird keiner gefunden, bleibt der ganze Text."""
    lines = _normalize(text).splitlines()
    collected, inside = [], False
    for line in lines:
        if _is_heading(line, REQUIREMENT_HEADINGS):
            inside = True
            continue
        if inside and _is_heading(line, END_HEADINGS):
            inside = False
            continue
        if inside:
            collected.append(line)
    return "\n".join(collected) if collected else text


def _is_nice(line: str) -> bool:
    low = line.lower()
    return any(re.search(rf"(?<!\w){re.escape(m)}(?!\w)", low) for m in NICE_MARKERS)


CLAUSE_SPLIT = re.compile(r"[,;()]|(?<!\w)(?:idealerweise|ideally|preferably|vorzugsweise)(?!\w)", re.IGNORECASE)


def _clauses(line: str) -> list[tuple[str, bool]]:
    """Teilt eine Zeile in Satzteile und markiert, welche "von Vorteil" sind.
    "Erfahrung im Verkauf, idealerweise in der Telekommunikation" -> Verkauf = Pflicht, Telekom = Plus.
    "Fluent in English, German is a plus" -> Englisch = Pflicht, Deutsch = Plus."""
    parts, last = [], 0
    for m in CLAUSE_SPLIT.finditer(line):
        parts.append(line[last : m.start()])
        last = m.start() if m.group(0)[0].isalpha() else m.end()  # Marker-Wort bleibt im nächsten Teil
    parts.append(line[last:])
    return [(p, _is_nice(p)) for p in parts if p.strip()]


def _option_is_nice(option: str, line: str) -> bool | None:
    """True/False, wenn die Option in einem Plus-/Pflicht-Satzteil steht; None, wenn nicht zuordenbar."""
    pattern = dict(_patterns()).get(option) or dict(_degree_patterns()).get(option)
    if pattern is None:
        return None
    flags = [nice for clause, nice in _clauses(line) if pattern.search(clause)]
    return all(flags) if flags else None


def _line_requirements(line: str) -> list[Requirement]:
    """Zerlegt eine Anforderungszeile in Requirements.
    - Ausbildungszeile mit Studienrichtungen -> EINE Anforderung, jede genannte Richtung genügt
      ("University degree in Law, Business Administration, or a related discipline").
    - Zeile mit "oder" / "or" / "/" -> die Skills der Zeile sind Alternativen.
    - sonst -> jeder Skill ist eine eigene Pflicht ("Deutsch und Englisch")."""
    line_nice = _is_nice(line)
    skills = find_skills(line)
    fields = find_degree_fields(line)
    reqs: list[Requirement] = []

    def nice_for(options: list[str]) -> bool:
        if not line_nice:
            return False
        flags = [f for f in (_option_is_nice(o, line) for o in options) if f is not None]
        return all(flags) if flags else True

    if fields:
        # In einer Ausbildungszeile gelten auch genannte Fachgebiete (z.B. "Corporate Governance") als Alternative
        options = fields + [s for s in skills if s not in DEGREE_LEVEL_SKILLS]
        reqs.append(Requirement(options=options, text=line, nice=nice_for(fields), kind="degree",
                                related_ok=bool(RELATED_WORDS.search(line))))
        return reqs
    levels = [s for s in skills if s in DEGREE_LEVEL_SKILLS]
    others = [s for s in skills if s not in DEGREE_LEVEL_SKILLS]
    if levels:  # "Abgeschlossene Lehre oder Studium" -> eine Anforderung
        reqs.append(Requirement(options=levels, text=line, nice=nice_for(levels), kind="degree"))
    if len(others) > 1 and OR_WORDS.search(line):
        reqs.append(Requirement(options=others, text=line, nice=nice_for(others)))
    else:
        reqs.extend(Requirement(options=[s], text=line, nice=nice_for([s])) for s in others)
    return reqs


def extract_requirements(description: str) -> tuple[list[Requirement], list[str], bool]:
    """Gibt (Anforderungen, nicht erkannte Pflicht-Zeilen, Abschnitt gefunden?) zurück."""
    text = _normalize(description)
    section = requirements_section(text)
    section_found = section != text
    reqs: list[Requirement] = []
    unchecked: list[str] = []
    seen: set[tuple[str, ...]] = set()
    for raw in section.splitlines():
        line = raw.strip(" \t-•*·")
        if not line or _is_heading(line, REQUIREMENT_HEADINGS):
            continue
        found = _line_requirements(line)
        if not found:
            # Nur im erkannten Abschnitt melden – sonst wäre jede Zeile des Inserats "unklar"
            if section_found and not _is_nice(line) and len(line) >= 20:
                unchecked.append(line)
            continue
        for req in found:
            key = tuple(sorted(req.options))
            if key not in seen:
                seen.add(key)
                reqs.append(req)
    # Was irgendwo Pflicht ist, ist nicht zusätzlich Nice-to-have
    must_keys = {tuple(sorted(r.options)) for r in reqs if not r.nice}
    reqs = [r for r in reqs if not (r.nice and tuple(sorted(r.options)) in must_keys)]
    return reqs, unchecked, section_found


def extract_rule_based(description: str) -> tuple[list[str], list[str]]:
    reqs, _, _ = extract_requirements(description)
    return [r.label for r in reqs if not r.nice], [r.label for r in reqs if r.nice]


LLM_PROMPT = """Lies die folgende Stellenbeschreibung. Gib NUR ein JSON-Objekt zurück, ohne weiteren Text:
{"must_have": [...], "nice_to_have": [...]}
- must_have: zwingend verlangte Fähigkeiten, Tools, Abschlüsse, Sprachen (kurze Begriffe, max. 12)
- nice_to_have: als "von Vorteil"/"wünschenswert"/"plus" bezeichnete Punkte (max. 8)
Erfinde nichts, was nicht im Text steht.

Stellenbeschreibung:
"""


def extract_llm(description: str) -> tuple[list[str], list[str]] | None:
    base, model = env("LLM_BASE_URL").rstrip("/"), env("LLM_MODEL")
    if not base or not model:
        return None
    headers = {"Authorization": f"Bearer {env('LLM_API_KEY')}"} if env("LLM_API_KEY") else {}
    try:
        resp = requests.post(
            f"{base}/chat/completions",
            headers=headers,
            json={"model": model, "temperature": 0, "messages": [{"role": "user", "content": LLM_PROMPT + description[:8000]}]},
            timeout=60,
        )
        resp.raise_for_status()
        content = resp.json()["choices"][0]["message"]["content"]
        data = json.loads(re.search(r"\{.*\}", content, re.DOTALL).group(0))
        return [str(s) for s in data.get("must_have", [])], [str(s) for s in data.get("nice_to_have", [])]
    except Exception as exc:
        log.warning("LLM-Extraktion fehlgeschlagen, nutze Regeln: %s", exc)
        return None


def apply_skills(job: Job, use_llm: bool = False) -> None:
    """Setzt requirements, must_have, nice_to_have, unchecked am Job."""
    result = extract_llm(job.description) if use_llm else None
    if result is not None:
        must, nice = result
        job.requirements = [Requirement([m]) for m in must] + [Requirement([n], nice=True) for n in nice]
        job.unchecked, job.section_found = [], True
    else:
        job.requirements, job.unchecked, job.section_found = extract_requirements(job.description)
    job.must_have = [r.label for r in job.requirements if not r.nice]
    job.nice_to_have = [r.label for r in job.requirements if r.nice]


def extract_skills(description: str, use_llm: bool = False) -> tuple[list[str], list[str]]:
    if use_llm:
        result = extract_llm(description)
        if result is not None:
            return result
    return extract_rule_based(description)
