from __future__ import annotations

from email.message import EmailMessage as MIMEEmail

from .models import EmailMessage


def render_draft(message: EmailMessage, source_email: str) -> MIMEEmail:
    mime = MIMEEmail()
    mime["From"] = source_email
    mime["To"] = message.sender_email
    mime["Subject"] = (
        message.subject if message.subject.lower().startswith("re:") else f"Re: {message.subject}"
    )
    if message.message_id_header:
        mime["In-Reply-To"] = message.message_id_header
        mime["References"] = " ".join(
            value for value in [message.references, message.message_id_header] if value
        )
    mime.set_content("Hello,\n\nThank you for your message. [REVIEW REQUIRED]\n\nBest regards,")
    return mime
