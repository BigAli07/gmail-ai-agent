from __future__ import annotations

from unittest.mock import Mock

from gmail_agent.gmail import GmailClient


def test_unread_query_is_recent_and_bounded() -> None:
    client = object.__new__(GmailClient)
    client.service = Mock()
    request = client.service.users().messages().list.return_value
    request.execute.return_value = {"messages": []}

    assert list(client.unread_messages(lookback_days=2, max_messages=50)) == []

    client.service.users().messages().list.assert_called_once()
    call = client.service.users().messages().list.call_args.kwargs
    assert "newer_than:2d" in call["q"]
    assert call["maxResults"] == 50


def test_configuration_default_batch_size_is_200() -> None:
    from gmail_agent.config import Settings

    settings = Settings(
        gmail_account_email="source@example.com",
        digest_recipient_email="digest@example.com",
    )
    assert settings.max_messages_per_run == 200
