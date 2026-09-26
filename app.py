"""Streamlit-Oberfläche. Start:  streamlit run app.py"""
from __future__ import annotations

import hmac
import logging

import streamlit as st
import yaml

from jobscout.config import add_company, env, load_companies
from jobscout.cv import pdf_to_text
from jobscout.detect import detect
from jobscout.emailer import build_email, send
from jobscout.pipeline import find_jobs, match_cv

logging.basicConfig(level=logging.INFO)
st.set_page_config(page_title="JobScout Schweiz", page_icon="🔎", layout="wide")
st.title("🔎 JobScout Schweiz")


def where(job) -> str:
    return f" ({job.location})" if job.location else ""


st.caption("Durchsucht Karriereseiten Schweizer Firmen, erkennt Must-Have-Skills und gleicht sie mit deinem CV ab.")

# Schutz für den Online-Betrieb: Ist APP_PASSWORD gesetzt, muss es zuerst eingegeben werden.
app_password = env("APP_PASSWORD")
if app_password and not st.session_state.get("authenticated"):
    entered = st.text_input("Passwort", type="password")
    if entered and hmac.compare_digest(entered, app_password):
        st.session_state["authenticated"] = True
        st.rerun()
    elif entered:
        st.error("Falsches Passwort.")
    st.stop()

# Ist ALLOWED_EMAILS gesetzt (Komma-getrennt), darf nur an diese Adressen gesendet werden.
allowed_emails = {e.strip().lower() for e in env("ALLOWED_EMAILS").split(",") if e.strip()}

tab_search, tab_add, tab_list = st.tabs(["Suche", "Firma hinzufügen", "Firmenliste"])

with tab_search:
    col1, col2 = st.columns(2)
    with col1:
        titles_raw = st.text_input("Jobtitel (mehrere mit Komma trennen)", placeholder="Data Engineer, Business Analyst")
        max_age = st.number_input("Nicht älter als (Tage)", min_value=1, max_value=365, value=14)
        min_employees = st.number_input("Mindestens Mitarbeitende", min_value=0, value=100, step=50,
                                        help="Firmen ohne Angabe in companies.yaml werden immer durchsucht.")
        swiss_only = st.checkbox("Nur Stellen in der Schweiz", value=True,
                                 help="Wichtig bei globalen Firmen (z.B. Novartis, Roche). Stellen ohne Ortsangabe bleiben drin.")
    with col2:
        cv_file = st.file_uploader("Dein CV (PDF)", type=["pdf"])
        email_to = st.text_input("E-Mail für die Resultate", placeholder="du@example.ch")
        top_n = st.slider("Wie viele Top-Treffer mailen?", 5, 50, 15)
    llm_ready = bool(env("LLM_BASE_URL") and env("LLM_MODEL"))
    use_llm = st.checkbox("KI für Skill-Erkennung nutzen", value=False, disabled=not llm_ready,
                          help="Nur aktiv, wenn LLM_BASE_URL und LLM_MODEL in .env gesetzt sind. Ohne KI: gratis Regel-Erkennung.")

    if st.button("Suchen", type="primary"):
        titles = [t.strip() for t in titles_raw.split(",") if t.strip()]
        if not load_companies(min_employees=min_employees):
            st.error("Keine Firmen in companies.yaml (mit genug Mitarbeitenden). Zuerst im Reiter 'Firma hinzufügen' Firmen erfassen.")
            st.stop()
        with st.status("Durchsuche Karriereseiten …", expanded=True) as status:
            jobs, errors = find_jobs(titles, int(max_age), use_llm=use_llm, min_employees=int(min_employees),
                                     progress=st.write, swiss_only=swiss_only)
            status.update(label=f"{len(jobs)} Stellen gefunden", state="complete", expanded=bool(errors))
        st.session_state["jobs"] = jobs
        st.session_state["search"] = (titles, int(max_age))
        if cv_file:
            st.session_state["cv_text"] = pdf_to_text(cv_file.getvalue())

    jobs = st.session_state.get("jobs")
    if jobs is not None:
        cv_text = st.session_state.get("cv_text", "")
        if cv_file and not cv_text:
            cv_text = st.session_state["cv_text"] = pdf_to_text(cv_file.getvalue())
        if cv_file and not cv_text:
            st.warning("Aus dem PDF liess sich kein Text lesen (gescanntes Bild?). Bitte CV als Text-PDF exportieren.")

        if cv_text:
            matches = match_cv(jobs, cv_text, top=len(jobs))
            st.subheader(f"Rangliste nach Übereinstimmung mit deinem CV ({len(matches)})")
            for m in matches:
                j = m.job
                with st.expander(f"{m.score:.0f}% · {j.title} – {j.company}{where(j)}"):
                    st.markdown(f"[Zum Inserat]({j.url}) · Datum: {j.effective_date or 'unbekannt'}"
                                + ("" if j.posted else " *(erstes Auftauchen, kein Datum im Inserat)*"))
                    st.markdown(f"**Must-Have:** {', '.join(j.must_have) or '– (keine erkannt)'}")
                    st.markdown(f"**Nice-to-have:** {', '.join(j.nice_to_have) or '–'}")
                    st.markdown(f"✅ **Hast du:** {', '.join(m.matched) or '–'}  \n❌ **Fehlt:** {', '.join(m.missing) or '–'}")

            if st.button("Top-Treffer per E-Mail senden"):
                if not email_to:
                    st.error("Bitte E-Mail-Adresse eingeben.")
                elif allowed_emails and email_to.strip().lower() not in allowed_emails:
                    st.error("An diese Adresse darf nicht gesendet werden (siehe ALLOWED_EMAILS).")
                else:
                    titles, age = st.session_state["search"]
                    try:
                        send(build_email(matches[:top_n], email_to, titles, age))
                        st.success(f"E-Mail an {email_to} gesendet.")
                    except Exception as exc:
                        st.error(f"Senden fehlgeschlagen: {exc}")
        else:
            st.subheader(f"Gefundene Stellen ({len(jobs)}) – CV hochladen für Ranking")
            for j in jobs:
                with st.expander(f"{j.title} – {j.company}{where(j)}"):
                    st.markdown(f"[Zum Inserat]({j.url}) · Datum: {j.effective_date or 'unbekannt'}")
                    st.markdown(f"**Must-Have:** {', '.join(j.must_have) or '– (keine erkannt)'}")
                    st.markdown(f"**Nice-to-have:** {', '.join(j.nice_to_have) or '–'}")

with tab_add:
    st.info("Online (z.B. Streamlit Cloud) gehen hier hinzugefügte Firmen beim Neustart der App verloren. "
            "Dauerhaft: den angezeigten Eintrag in companies.yaml auf GitHub eintragen.")
    st.write("Füge die URL der Karriereseite ein. Die App erkennt, welches Bewerbersystem die Firma nutzt.")
    url = st.text_input("Karriereseite-URL", placeholder="https://www.firma.ch/karriere")
    if st.button("Erkennen") and url:
        try:
            st.session_state["detected"] = detect(url)
        except Exception as exc:
            st.error(f"Seite konnte nicht geladen werden: {exc}")
    found = st.session_state.get("detected")
    if found:
        if found.get("hinweis"):
            st.warning(found["hinweis"])
        else:
            st.success(f"Erkannt: {found['source']} → {found['target']}")
        name = st.text_input("Firmenname")
        employees = st.number_input("Anzahl Mitarbeitende (z.B. aus Geschäftsbericht)", min_value=0, value=0)
        source = st.text_input("Quelle", value=found["source"])
        target = st.text_input("Kennung/URL", value=found["target"])
        if st.button("Zur Liste hinzufügen"):
            if not name or employees <= 0:
                st.error("Bitte Name und Mitarbeiterzahl angeben.")
            else:
                entry = {"name": name, "employees": int(employees), "source": source, "target": target}
                if found.get("domain"):
                    entry["domain"] = found["domain"]
                try:
                    add_company(entry)
                    st.success(f"{name} hinzugefügt. Eintrag für companies.yaml (zum Kopieren):")
                    st.code(yaml.safe_dump([entry], allow_unicode=True, sort_keys=False), language="yaml")
                    st.session_state.pop("detected", None)
                except ValueError as exc:
                    st.error(str(exc))

with tab_list:
    companies = load_companies(min_employees=0)
    if companies:
        st.dataframe([{"Name": c.name, "Mitarbeitende": c.employees if c.employees is not None else "unbekannt",
                       "Startup": "ja" if c.extra.get("startup") else "", "Quelle": c.source, "Kennung/URL": c.target}
                      for c in companies],
                     use_container_width=True)
    else:
        st.info("Noch keine Firmen erfasst.")
    st.caption("Bearbeiten/Löschen: Datei companies.yaml mit einem Texteditor öffnen.")
