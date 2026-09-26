import json
from datetime import date, timedelta

import pytest

from jobscout import config, detect, storage
from jobscout.emailer import build_email
from jobscout.matcher import rank
from jobscout.models import Company, Job
from jobscout.pipeline import filter_age
from jobscout.scrapers import ats, http, title_filter
from jobscout.scrapers.jsonld import jsonld as scrape_jsonld
from jobscout.skills import extract_rule_based, find_skills


class FakeResp:
    def __init__(self, data=None, text="", url=""):
        self._data, self.text, self.url = data, text, url
        self.content = text.encode()

    def json(self):
        return self._data


def fake_get(routes):
    def get(url, **kwargs):
        for prefix, resp in routes.items():
            if url.startswith(prefix):
                return resp
        raise AssertionError(f"unerwartete URL {url}")
    return get


JOB_TEXT = """Ihre Aufgaben
Du baust Datenpipelines.
Ihr Profil
Abgeschlossenes Studium in Informatik
Mehrjährige Erfahrung mit Python und SQL
Kenntnisse in Azure und Docker
Erfahrung mit Kubernetes ist von Vorteil
Sehr gute Deutsch- und Englischkenntnisse
Wir bieten
Flexible Arbeitszeiten und Python-Kurse
"""


def test_skill_extraction_separates_must_and_nice():
    must, nice = extract_rule_based(JOB_TEXT)
    assert {"Python", "SQL", "Azure", "Docker", "Studium Informatik"} <= set(must)
    assert "Kubernetes" in nice and "Kubernetes" not in must


def test_skill_word_boundaries():
    assert "Java" not in find_skills("Wir nutzen JavaScript")
    assert "JavaScript" in find_skills("Wir nutzen JavaScript")
    assert "C#" in find_skills("Erfahrung mit C# und .NET")
    assert "SAP" not in find_skills("sapiens")


def test_title_filter():
    wanted = title_filter(["Data Engineer"])
    assert wanted("Senior Data Engineer (m/w/d) 80-100%")
    assert not wanted("Data Analyst")
    assert title_filter([])("irgendwas")


def test_age_filter_uses_first_seen_when_no_date():
    today = date(2026, 9, 26)
    old = Job("A", "x", "u1", posted=today - timedelta(days=30))
    new = Job("A", "y", "u2", posted=today - timedelta(days=3))
    unknown = Job("A", "z", "u3", first_seen=today)
    assert filter_age([old, new, unknown], 14, today) == [new, unknown]


def test_storage_keeps_first_seen(tmp_path):
    db = tmp_path / "s.sqlite"
    j = Job("A", "t", "u")
    storage.stamp_first_seen([j], db, today=date(2026, 9, 1))
    j2 = Job("A", "t", "u")
    storage.stamp_first_seen([j2], db, today=date(2026, 9, 20))
    assert j2.first_seen == date(2026, 9, 1)


def test_ranking():
    good = Job("A", "Data Engineer", "u1", must_have=["Python", "SQL", "Azure"])
    bad = Job("B", "SAP Consultant", "u2", must_have=["SAP", "ABAP"])
    matches = rank([bad, good], "Data Engineer mit Python, SQL und Azure")
    assert matches[0].job is good and matches[0].score > 90
    assert matches[1].missing == ["SAP", "ABAP"]


def test_smartrecruiters(monkeypatch):
    base = "https://api.smartrecruiters.com/v1/companies/Acme/postings"
    monkeypatch.setattr(ats.http, "get", fake_get({
        f"{base}/1": FakeResp({"postingUrl": "https://jobs.smartrecruiters.com/Acme/1",
                               "jobAd": {"sections": {"qualifications": {"text": "<ul><li>Python</li></ul>"}}}}),
        base: FakeResp({"totalFound": 2, "content": [
            {"id": "1", "name": "Data Engineer", "releasedDate": "2026-09-20T08:00:00.000Z", "location": {"city": "Zürich", "country": "ch"}},
            {"id": "2", "name": "Koch", "releasedDate": "2026-09-20T08:00:00.000Z"}]}),
    }))
    jobs = ats.smartrecruiters(Company("Acme", 500, "smartrecruiters", "Acme"), title_filter(["engineer"]))
    assert len(jobs) == 1 and jobs[0].posted == date(2026, 9, 20) and "Python" in jobs[0].description


def test_greenhouse_double_escaped_html(monkeypatch):
    monkeypatch.setattr(ats.http, "get", fake_get({"https://boards-api.greenhouse.io": FakeResp({"jobs": [
        {"title": "Engineer", "absolute_url": "https://x", "updated_at": "2026-09-10T00:00:00-04:00",
         "location": {"name": "Basel"}, "content": "&lt;p&gt;Python&lt;/p&gt;"}]})}))
    jobs = ats.greenhouse(Company("G", 200, "greenhouse", "g"), title_filter([]))
    assert jobs[0].description == "Python" and jobs[0].posted == date(2026, 9, 10)


def test_lever(monkeypatch):
    monkeypatch.setattr(ats.http, "get", fake_get({"https://api.lever.co": FakeResp([
        {"text": "Engineer", "hostedUrl": "https://x", "createdAt": 1788000000000, "categories": {"location": "Bern"},
         "descriptionPlain": "Hi", "lists": [{"text": "Requirements", "content": "<li>Go</li>"}]}])}))
    jobs = ats.lever(Company("L", 200, "lever", "l"), title_filter([]))
    assert jobs[0].location == "Bern" and "Requirements" in jobs[0].description and jobs[0].posted


def test_personio(monkeypatch):
    xml = """<?xml version="1.0"?><workzag-jobs><position><id>7</id><office>Luzern</office><name>Engineer</name>
    <createdAt>2026-09-15T10:00:00+00:00</createdAt><jobDescriptions><jobDescription><name>Profil</name>
    <value><![CDATA[<p>Python</p>]]></value></jobDescription></jobDescriptions></position></workzag-jobs>"""
    monkeypatch.setattr(ats.http, "get", fake_get({"https://p.jobs.personio.de/xml": FakeResp(text=xml)}))
    jobs = ats.personio(Company("P", 200, "personio", "p"), title_filter([]))
    assert jobs[0].url == "https://p.jobs.personio.de/job/7" and "Python" in jobs[0].description


def test_recruitee(monkeypatch):
    monkeypatch.setattr(ats.http, "get", fake_get({"https://r.recruitee.com": FakeResp({"offers": [
        {"title": "Engineer", "careers_url": "https://x", "published_at": "2026-09-01 10:00:00 UTC",
         "location": "Genf", "description": "<p>A</p>", "requirements": "<p>SQL</p>"}]})}))
    jobs = ats.recruitee(Company("R", 200, "recruitee", "r"), title_filter([]))
    assert "SQL" in jobs[0].description and jobs[0].posted == date(2026, 9, 1)


def test_workday(monkeypatch):
    api = "https://acme.wd3.myworkdayjobs.com/wday/cxs/acme/Careers"
    monkeypatch.setattr(ats.http, "post_json", lambda url, payload: FakeResp(
        {"total": 1, "jobPostings": [{"title": "Engineer", "externalPath": "/job/Zurich/Engineer_R1", "postedOn": "Posted 3 Days Ago"}]}
        if payload["offset"] == 0 else {"total": 0, "jobPostings": []}))
    monkeypatch.setattr(ats.http, "get", fake_get({f"{api}/job": FakeResp({"jobPostingInfo": {"jobDescription": "<p>Python</p>"}})}))
    jobs = ats.workday(Company("W", 900, "workday", "https://acme.wd3.myworkdayjobs.com/de-DE/Careers"), title_filter([]))
    assert jobs[0].posted == date.today() - timedelta(days=3) and jobs[0].description == "Python"


def test_jsonld_follows_links(monkeypatch):
    listing = '<a href="/jobs/1">Data Engineer 100%</a><a href="/jobs/2">Koch</a><a href="https://other.ch/x">Data Engineer</a>'
    posting = {"@context": "https://schema.org", "@type": "JobPosting", "title": "Data Engineer", "datePosted": "2026-09-22",
               "description": "<p>Python</p>", "jobLocation": {"address": {"addressLocality": "Zug", "addressCountry": "CH"}}}
    detail = f'<script type="application/ld+json">{json.dumps({"@graph": [posting]})}</script>'
    monkeypatch.setattr(http, "get", fake_get({
        "https://firma.ch/jobs/1": FakeResp(text=detail), "https://firma.ch/karriere": FakeResp(text=listing)}))
    jobs = scrape_jsonld(Company("F", 300, "jsonld", "https://firma.ch/karriere"), title_filter(["data engineer"]))
    assert len(jobs) == 1 and jobs[0].location == "Zug, CH" and jobs[0].url == "https://firma.ch/jobs/1"


@pytest.mark.parametrize("html,expected", [
    ('<iframe src="https://careers.smartrecruiters.com/AcmeAG">', {"source": "smartrecruiters", "target": "AcmeAG"}),
    ('<script src="https://boards.greenhouse.io/embed/job_board/js?for=acme"></script>', {"source": "greenhouse", "target": "acme"}),
    ('<a href="https://jobs.lever.co/acme">', {"source": "lever", "target": "acme"}),
    ('<a href="https://acme-ag.jobs.personio.de/">', {"source": "personio", "target": "acme-ag", "domain": "jobs.personio.de"}),
    ('<a href="https://acme.wd103.myworkdayjobs.com/en-US/External/job/x">', {"source": "workday", "target": "https://acme.wd103.myworkdayjobs.com/en-US/External"}),
])
def test_detect(html, expected):
    assert detect.detect_in(html, "https://acme.ch/jobs") == expected


def test_companies_yaml_roundtrip(tmp_path):
    path = tmp_path / "c.yaml"
    path.write_text("# Kommentar\ncompanies: []\n", encoding="utf-8")
    config.add_company({"name": "Gross AG", "employees": 500, "source": "lever", "target": "gross"}, path)
    config.add_company({"name": "Klein AG", "employees": 20, "source": "lever", "target": "klein"}, path)
    assert "# Kommentar" in path.read_text()
    assert [c.name for c in config.load_companies(path)] == ["Gross AG"]
    with pytest.raises(ValueError):
        config.add_company({"name": "Gross AG", "employees": 1, "source": "lever", "target": "x"}, path)


def test_email_escapes_html():
    job = Job("A<b>", "Dev", "https://x?a=1&b=2", must_have=["Python"])
    msg = build_email(rank([job], "Python"), "me@example.ch", ["Dev"], 14)
    html_part = msg.get_body(("html",)).get_content()
    assert "A&lt;b&gt;" in html_part and "a=1&amp;b=2" in html_part


def test_send_uses_starttls_and_login(monkeypatch):
    from jobscout import emailer

    calls = []

    class FakeSMTP:
        def __init__(self, host, port, timeout):
            calls.append(("connect", host, port))

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def starttls(self, context):
            calls.append(("starttls",))

        def login(self, user, pw):
            calls.append(("login", user))

        def send_message(self, msg):
            calls.append(("send", msg["To"]))

    for k, v in {"SMTP_HOST": "smtp.test", "SMTP_PORT": "587", "SMTP_USER": "me@test", "SMTP_PASSWORD": "x"}.items():
        monkeypatch.setenv(k, v)
    monkeypatch.setattr(emailer.smtplib, "SMTP", FakeSMTP)
    emailer.send(build_email([], "you@test", [], 14))
    assert calls == [("connect", "smtp.test", 587), ("starttls",), ("login", "me@test"), ("send", "you@test")]


def test_is_swiss():
    from jobscout.scrapers.filters import is_swiss

    assert is_swiss("Basel") and is_swiss("Zürich, ch") and is_swiss("Switzerland - Rotkreuz") and is_swiss("Genève")
    assert is_swiss("East Hanover, NJ, USA") is False and is_swiss("Munich, de") is False
    assert is_swiss("3 Locations") is None and is_swiss("") is None


def test_swiss_filter_skips_detail_download(monkeypatch):
    base = "https://api.smartrecruiters.com/v1/companies/Acme/postings"
    monkeypatch.setattr(ats.http, "get", fake_get({
        f"{base}/1": FakeResp({"jobAd": {"sections": {}}}),
        base: FakeResp({"totalFound": 2, "content": [
            {"id": "1", "name": "Engineer", "location": {"city": "Zug", "country": "ch"}},
            {"id": "2", "name": "Engineer", "location": {"city": "Boston", "country": "us"}}]}),
    }))  # /2 ist nicht gemockt: würde der Filter versagen, schlägt der Test fehl
    jobs = ats.smartrecruiters(Company("Acme", 500, "smartrecruiters", "Acme"), title_filter([], swiss_only=True))
    assert [j.location for j in jobs] == ["Zug, ch"]


def test_workday_searches_per_title_and_dedupes(monkeypatch):
    api = "https://acme.wd3.myworkdayjobs.com/wday/cxs/acme/Careers"
    searches = []

    def post(url, payload):
        searches.append(payload["searchText"])
        return FakeResp({"total": 2, "jobPostings": [
            {"title": "Data Engineer", "externalPath": "/job/Basel/DE_1", "locationsText": "Basel"},
            {"title": "Data Engineer", "externalPath": "/job/Boston/DE_2", "locationsText": "Boston, MA"}]})

    monkeypatch.setattr(ats.http, "post_json", post)
    monkeypatch.setattr(ats.http, "get", fake_get({f"{api}/job/Basel": FakeResp({"jobPostingInfo": {"location": "Basel", "jobDescription": "x"}})}))
    jobs = ats.workday(Company("W", None, "workday", "https://acme.wd3.myworkdayjobs.com/Careers"),
                       title_filter(["Data Engineer", "Engineer"], swiss_only=True))
    assert searches == ["Data Engineer", "Engineer"]
    assert len(jobs) == 1 and jobs[0].location == "Basel"


def test_import_json(tmp_path):
    from jobscout.importer import import_json

    src = tmp_path / "c.json"
    src.write_text(json.dumps([
        {"name": "Novartis", "ats": "workday", "url": "https://novartis.wd3.myworkdayjobs.com", "site": "Novartis_Careers", "hq": "Basel"},
        {"name": "On", "ats": "greenhouse", "token": "onrunning", "startup": False},
        {"name": "Bot", "ats": "lever", "token": "bot", "startup": True, "employees": 50},
        {"name": "Kaputt", "ats": "taleo", "token": "x"},
    ]), encoding="utf-8")
    yml = tmp_path / "c.yaml"
    yml.write_text("companies: []\n", encoding="utf-8")
    added, skipped = import_json(src, yml)
    assert added == ["Novartis", "On", "Bot"] and len(skipped) == 1
    companies = {c.name: c for c in config.load_companies(yml, min_employees=100)}
    assert set(companies) == {"Novartis", "On"}  # unbekannte Grösse bleibt, bekannte 50 fällt raus
    assert companies["Novartis"].target == "https://novartis.wd3.myworkdayjobs.com/Novartis_Careers"
    assert import_json(src, yml)[0] == []  # zweiter Import: keine Duplikate


SANDOZ = """Your Key Responsibilities:
Coordinate governance-related KYC, AML, due diligence and procurement-related activities.
What you’ll bring to the role:
Essential and Desirable Requirements:
University degree in Law, Business Administration, Corporate Governance, or a related discipline.
Experience in corporate governance, corporate legal, company secretarial, or a comparable function.
Good understanding of Swiss corporate law and governance requirements.
Strong organizational, coordination, and execution skills, with a pragmatic approach.
Fluent in German and English, both written and spoken.
Why Sandoz?
We have an agile and collegiate environment.
"""


def test_degree_field_is_a_knockout():
    from jobscout.skills import apply_skills

    job = Job("Sandoz", "Specialist Group Governance Legal", "u", description=SANDOZ)
    apply_skills(job)
    assert job.section_found  # typografischer Apostroph in "What you’ll bring"
    assert "Scrum / Agile" not in job.must_have and "Einkauf / Procurement" not in job.must_have
    assert job.must_have[0] == "Studium Recht oder Studium BWL / Business oder Corporate Governance"
    assert "Gesellschaftsrecht" in job.must_have
    assert any("organizational" in line for line in job.unchecked)

    it = rank([job], "Master of Science in Informatik, ETH Zürich\nPython, SQL, Stakeholder Management, Deutsch, Englisch")[0]
    assert it.knockout and it.score <= 40
    bwl = rank([job], "Bachelor in Business Administration, HSG\nDeutsch, Englisch")[0]
    assert not bwl.knockout  # BWL ist laut Inserat ausdrücklich zulässig
    jurist = rank([job], "MLaw, Universität Zürich\nGesellschaftsrecht, Corporate Governance, Company Secretary\nDeutsch, Englisch")[0]
    assert not jurist.knockout and jurist.score > 90


def test_or_and_and_groups():
    from jobscout.skills import extract_requirements

    reqs, _, _ = extract_requirements("Ihr Profil\nPython oder Java\nDeutsch und Englisch\nAbgeschlossene Lehre oder Studium")
    labels = [r.label for r in reqs]
    assert "Python oder Java" in labels and "Deutsch" in labels and "Englisch" in labels
    assert "Hochschulabschluss oder Lehre / EFZ" in labels


def test_law_outside_degree_line_is_not_a_degree():
    from jobscout.skills import cv_degree_fields, find_degree_fields

    assert find_degree_fields("Good understanding of Swiss corporate law") == []
    assert find_degree_fields("Master in Law (MLaw)") == ["Studium Recht"]
    assert cv_degree_fields("Master of Science\nInformatik, ETH Zürich") == ["Studium Informatik"]
    assert "Stakeholder Management" in find_skills("collaborate with stakeholders")
