from __future__ import annotations

import html
import smtplib
import ssl
from email.message import EmailMessage

from .config import env
from .models import Match


def build_email(matches: list[Match], to_addr: str, titles: list[str], max_age_days: int) -> EmailMessage:
    msg = EmailMessage()
    msg["Subject"] = f"JobScout: {len(matches)} passende Stellen"
    msg["From"] = env("SMTP_FROM") or env("SMTP_USER")
    msg["To"] = to_addr

    search = ", ".join(titles) or "alle Titel"
    plain = [f"Suche: {search} | nicht älter als {max_age_days} Tage", ""]
    rows = []
    for i, m in enumerate(matches, 1):
        j = m.job
        when = j.effective_date.isoformat() if j.effective_date else "unbekannt"
        plain += [
            f"{i}. {j.title} – {j.company}" + (f" ({j.location})" if j.location else "") + f" – Match {m.score:.0f}%",
            f"   Datum: {when}",
            f"   Must-Have: {', '.join(j.must_have) or '–'}",
            f"   Fehlt dir: {', '.join(m.missing) or '–'}",
            *[f"   ACHTUNG Ausschlusskriterium – {ko}" for ko in m.knockout],
            *[f"   Selbst prüfen: {line}" for line in m.unchecked],
            f"   {j.url}",
            "",
        ]
        rows.append(
            f"<tr><td><b>{m.score:.0f}%</b></td>"
            f"<td><a href='{html.escape(j.url, quote=True)}'>{html.escape(j.title)}</a><br>"
            f"<small>{html.escape(j.company)} · {html.escape(j.location)} · {when}</small></td>"
            f"<td><small><b>Must-Have:</b> {html.escape(', '.join(j.must_have) or '–')}<br>"
            f"<b>Fehlt dir:</b> {html.escape(', '.join(m.missing) or '–')}"
            + "".join(f"<br><b style='color:#b00020'>⚠️ Ausschlusskriterium – {html.escape(ko)}</b>" for ko in m.knockout)
            + "".join(f"<br>🔍 Selbst prüfen: {html.escape(line)}" for line in m.unchecked)
            + "</small></td></tr>"
        )
    msg.set_content("\n".join(plain))
    msg.add_alternative(
        f"<p>Suche: <b>{html.escape(search)}</b> · nicht älter als {max_age_days} Tage</p>"
        "<table cellpadding='6' style='border-collapse:collapse;font-family:sans-serif'>"
        "<tr><th>Match</th><th>Stelle</th><th>Skills</th></tr>" + "".join(rows) + "</table>"
        "<p><small>Der Match-Wert ist eine automatische Schätzung – bitte Inserat selbst lesen.</small></p>",
        subtype="html",
    )
    return msg


def send(msg: EmailMessage) -> None:
    host, port = env("SMTP_HOST", "smtp.gmail.com"), int(env("SMTP_PORT", "587"))
    user, password = env("SMTP_USER"), env("SMTP_PASSWORD")
    if not user or not password:
        raise RuntimeError("SMTP_USER / SMTP_PASSWORD fehlen. Siehe .env.example bzw. README.")
    context = ssl.create_default_context()
    if port == 465:
        with smtplib.SMTP_SSL(host, port, context=context, timeout=30) as server:
            server.login(user, password)
            server.send_message(msg)
    else:
        with smtplib.SMTP(host, port, timeout=30) as server:
            server.starttls(context=context)
            server.login(user, password)
            server.send_message(msg)
