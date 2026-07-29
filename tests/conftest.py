from __future__ import annotations

from datetime import UTC, datetime

import pytest

from gmail_agent.models import EmailMessage


@pytest.fixture
def make_message():
    def factory(
        text: str,
        *,
        message_id: str = "m1",
        sender: str = "sender@example.com",
        subject: str = "Hello",
    ) -> EmailMessage:
        return EmailMessage(
            id=message_id,
            thread_id=f"t-{message_id}",
            sender=sender,
            sender_email=sender,
            subject=subject,
            received_at=datetime.now(UTC),
            plain_body=text,
        )

    return factory
