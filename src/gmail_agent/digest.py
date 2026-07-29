from __future__ import annotations

import html
from datetime import datetime
from email.message import EmailMessage as MIMEEmail
from zoneinfo import ZoneInfo

from .models import Analysis, Category, EmailMessage

SECTION_NAMES = {
    Category.SJSU: "SJSU",
    Category.AI_NEWS: "AI News",
    Category.INTERNSHIP: "Internships",
    Category.HACKATHON: "Hackathons",
    Category.SCHOLARSHIP: "Scholarships",
    Category.OTHER_IMPORTANT_NEWS: "Other Important News",
}


def render_digest(
    entries: list[tuple[EmailMessage, Analysis, bool]],
    source_email: str,
    recipient: str,
    now: datetime,
) -> MIMEEmail:
    local = now.astimezone(ZoneInfo("America/Los_Angeles"))
    subject = f"Important Email Digest — {local:%Y-%m-%d %H}:00"
    plain_sections: list[str] = []
    html_sections: list[str] = []
    for category, title in SECTION_NAMES.items():
        selected = [entry for entry in entries if entry[1].category == category]
        if not selected:
            continue
        plain_items = []
        html_items = []
        for message, analysis, drafted in selected:
            link = f"https://mail.google.com/mail/u/0/#inbox/{message.id}"
            deadlines = ", ".join(analysis.deadlines) or "None identified"
            actions = ", ".join(analysis.action_items) or "None identified"
            plain_items.append(
                f"From: {message.sender} <{message.sender_email}>\nSubject: {message.subject}\n"
                f"Received: {message.received_at.isoformat()}\nCategory: {title}\n"
                f"Summary: {analysis.summary}\nWhy important: {analysis.reason}\n"
                f"Deadlines: {deadlines}\nActions: {actions}\n"
                f"Draft created: {'Yes' if drafted else 'No'}\n"
                f"Gmail: {link}"
            )
            html_items.append(
                "<article>"
                f"<h3>{html.escape(message.subject)}</h3>"
                f"<p><strong>From:</strong> {html.escape(message.sender)} "
                f"&lt;{html.escape(message.sender_email)}&gt;<br>"
                f"<strong>Received:</strong> {html.escape(message.received_at.isoformat())}<br>"
                f"<strong>Category:</strong> {html.escape(title)}<br>"
                f"<strong>Summary:</strong> {html.escape(analysis.summary)}<br>"
                f"<strong>Why important:</strong> {html.escape(analysis.reason)}<br>"
                f"<strong>Deadlines:</strong> {html.escape(deadlines)}<br>"
                f"<strong>Actions:</strong> {html.escape(actions)}<br>"
                f"<strong>Draft created:</strong> {'Yes' if drafted else 'No'}<br>"
                f'<a href="{html.escape(link, quote=True)}">Open in Gmail</a></p></article>'
            )
        plain_sections.append(f"{title}\n{'=' * len(title)}\n" + "\n\n".join(plain_items))
        html_sections.append(
            f"<section><h2>{html.escape(title)}</h2>{''.join(html_items)}</section>"
        )
    mime = MIMEEmail()
    mime["From"] = source_email
    mime["To"] = recipient
    mime["Subject"] = subject
    mime.set_content("\n\n".join(plain_sections))
    mime.add_alternative(
        "<html><body><h1>Important Email Digest</h1>" + "".join(html_sections) + "</body></html>",
        subtype="html",
    )
    return mime
