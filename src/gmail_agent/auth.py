from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

GMAIL_SCOPES = [
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/gmail.compose",
    "openid",
    "https://www.googleapis.com/auth/userinfo.email",
]


class AccountMismatchError(RuntimeError):
    """OAuth identity differs from the explicitly configured source account."""


def load_credentials(
    credentials_file: Path,
    token_file: Path,
    *,
    flow_factory: Callable[..., Any] = InstalledAppFlow.from_client_secrets_file,
) -> Credentials:
    credentials: Credentials | None = None
    if token_file.exists():
        credentials = Credentials.from_authorized_user_file(  # type: ignore[no-untyped-call]
            str(token_file), GMAIL_SCOPES
        )
    if credentials and credentials.expired and credentials.refresh_token:
        credentials.refresh(Request())  # type: ignore[no-untyped-call]
    elif not credentials or not credentials.valid:
        flow = flow_factory(str(credentials_file), GMAIL_SCOPES)
        credentials = flow.run_local_server(port=0)
    token_file.parent.mkdir(parents=True, exist_ok=True)
    token_file.write_text(credentials.to_json(), encoding="utf-8")
    return credentials


def verify_authenticated_account(
    credentials: Credentials,
    expected_email: str,
    *,
    request_get: Callable[..., Any] | None = None,
) -> str:
    """Verify OAuth identity before any Gmail API service is created or called."""
    if request_get is None:
        import requests

        request_get = requests.get
    if not credentials.valid:
        credentials.refresh(Request())  # type: ignore[no-untyped-call]
    response = request_get(
        "https://openidconnect.googleapis.com/v1/userinfo",
        headers={"Authorization": f"Bearer {credentials.token}"},
        timeout=15,
    )
    response.raise_for_status()
    authenticated = str(response.json().get("email", "")).strip().lower()
    expected = expected_email.strip().lower()
    if not authenticated or authenticated != expected:
        raise AccountMismatchError(
            "OAuth account mismatch: authenticated as "
            f"{authenticated or '<unknown>'}, but GMAIL_ACCOUNT_EMAIL is {expected}. "
            "Stopped before reading or modifying any email."
        )
    return authenticated


def redact_token_file(path: Path) -> dict[str, Any]:
    """Return token metadata without exposing token values (diagnostics only)."""
    data = json.loads(path.read_text(encoding="utf-8"))
    return {key: ("<redacted>" if "token" in key else value) for key, value in data.items()}
