from __future__ import annotations

from unittest.mock import Mock

import pytest

from gmail_agent.auth import AccountMismatchError, verify_authenticated_account


def test_matching_oauth_identity_is_accepted() -> None:
    credentials = Mock(valid=True, token="secret")
    response = Mock()
    response.json.return_value = {"email": "Owner@Example.com"}
    authenticated = verify_authenticated_account(
        credentials, "owner@example.com", request_get=Mock(return_value=response)
    )
    assert authenticated == "owner@example.com"


def test_mismatch_stops_with_clear_error_before_gmail_access() -> None:
    credentials = Mock(valid=True, token="secret")
    response = Mock()
    response.json.return_value = {"email": "wrong@example.com"}
    with pytest.raises(AccountMismatchError, match="Stopped before reading or modifying"):
        verify_authenticated_account(
            credentials, "owner@example.com", request_get=Mock(return_value=response)
        )
