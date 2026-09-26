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
    "Compliance": ["compliance", "aml", "kyc", "finma"], "Audit": ["audit", "revision", "wirtschaftsprüfung"],
    "Sales / Verkauf": ["verkauf", "sales", "akquisition", "business development", "key account"],
    "Marketing": ["marketing", "seo", "content marketing", "social media"], "CRM": ["crm"],
    "Einkauf / Procurement": ["einkauf", "procurement", "beschaffung"], "Supply Chain": ["supply chain", "logistik", "logistics"],
    # Technik / Ingenieurwesen / Gesundheit
    "CAD": ["cad", "autocad", "solidworks", "catia", "inventor"], "Elektrotechnik": ["elektrotechnik", "electrical engineering"],
    "Maschinenbau": ["maschinenbau", "mechanical engineering"], "Automation / SPS": ["sps", "plc", "automation", "automatisierung", "siemens tia"],
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

REQUIREMENT_HEADINGS = [
    "ihr profil", "dein profil", "ihre qualifikationen", "deine qualifikationen", "anforderungen", "anforderungsprofil",
    "was sie mitbringen", "was du mitbringst", "das bringen sie mit", "das bringst du mit", "sie bringen mit", "du bringst mit",
    "voraussetzungen", "ihre kompetenzen", "deine kompetenzen", "wen wir suchen", "what you bring", "what you'll bring",
    "your profile", "requirements", "qualifications", "who you are", "skills", "must have", "must-have",
    "what we're looking for", "what we are looking for", "about you", "votre profil", "exigences", "il tuo profilo", "requisiti",
]
END_HEADINGS = [
    "wir bieten", "was wir bieten", "unser angebot", "deine vorteile", "ihre vorteile", "benefits", "what we offer",
    "we offer", "why join", "über uns", "about us", "kontakt", "contact", "bewerbung", "nous offrons", "ihre aufgaben",
    "deine aufgaben", "your tasks", "your responsibilities", "responsibilities", "offriamo",
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


@lru_cache(maxsize=1)
def _patterns() -> list[tuple[str, re.Pattern]]:
    skills = {**SKILLS, **_load_extra()}
    compiled = []
    for name, aliases in skills.items():
        alt = "|".join(re.escape(a) for a in sorted(aliases, key=len, reverse=True))
        # Wortgrenzen, die auch Sonderzeichen wie C#, C++, .NET erlauben
        compiled.append((name, re.compile(rf"(?<![\w]){'(?:' + alt + ')'}(?![\w+#])", re.IGNORECASE)))
    return compiled


def find_skills(text: str) -> list[str]:
    """Alle bekannten Skills, die im Text vorkommen (Reihenfolge wie im Wörterbuch)."""
    return [name for name, pattern in _patterns() if pattern.search(text or "")]


def _is_heading(line: str, headings: list[str]) -> bool:
    clean = line.lower().strip(" :#*-•\t")
    return len(clean) <= 60 and any(clean.startswith(h) or clean == h for h in headings)


def requirements_section(text: str) -> str:
    """Schneidet den Anforderungs-Abschnitt aus. Wird keiner gefunden, bleibt der ganze Text."""
    lines = text.splitlines()
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


def extract_rule_based(description: str) -> tuple[list[str], list[str]]:
    section = requirements_section(description)
    must, nice = [], []
    for line in section.splitlines():
        target = nice if _is_nice(line) else must
        for skill in find_skills(line):
            if skill not in must and skill not in target:
                target.append(skill)
    nice = [s for s in nice if s not in must]
    return must, nice


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


def extract_skills(description: str, use_llm: bool = False) -> tuple[list[str], list[str]]:
    if use_llm:
        result = extract_llm(description)
        if result is not None:
            return result
    return extract_rule_based(description)
