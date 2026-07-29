from __future__ import annotations

import re
from datetime import UTC, datetime
from email.message import Message
from email.utils import parseaddr, parsedate_to_datetime

from .models import EmailMessage

URL_RE = re.compile(r"https?://[^\s<>\"']+")


def _decode_part(part: Message) -> str:
    payload = part.get_payload(decode=True)
    if not isinstance(payload, bytes):
        return ""
    return payload.decode(part.get_content_charset() or "utf-8", errors="replace")


def parse_raw_message(message_id: str, thread_id: str, mime: Message) -> EmailMessage:
    plain: list[str] = []
    html: list[str] = []
    attachments: list[str] = []
    for part in mime.walk():
        filename = part.get_filename()
        if filename:
            attachments.append(filename)
            continue
        if part.get_content_type() == "text/plain":
            plain.append(_decode_part(part))
        elif part.get_content_type() == "text/html":
            html.append(_decode_part(part))
    sender_name, sender_email = parseaddr(str(mime.get("From", "")))
    try:
        received = parsedate_to_datetime(str(mime.get("Date", "")))
        received = received.astimezone(UTC)
    except (TypeError, ValueError):
        received = datetime.now(UTC)
    combined = "\n".join(plain + html)
    return EmailMessage(
        id=message_id,
        thread_id=thread_id,
        sender=sender_name or sender_email,
        sender_email=sender_email.lower(),
        subject=str(mime.get("Subject", "(no subject)")),
        received_at=received,
        plain_body="\n".join(plain),
        html_body="\n".join(html),
        attachment_filenames=attachments,
        message_id_header=mime.get("Message-ID"),
        references=mime.get("References"),
        list_id=mime.get("List-ID"),
        auto_submitted=mime.get("Auto-Submitted"),
        links=URL_RE.findall(combined)[:20],
    )
