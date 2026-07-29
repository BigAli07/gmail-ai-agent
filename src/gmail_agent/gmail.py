from __future__ import annotations

import base64
from collections.abc import Iterable
from email import message_from_bytes
from email.message import EmailMessage as MIMEEmail
from email.policy import default

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

from .models import EmailMessage
from .parser import parse_raw_message

LABELS = {
    "important": "AI-Agent/Important",
    "low": "AI-Agent/Low-Priority",
    "processed": "AI-Agent/Processed",
    "draft": "AI-Agent/Draft-Created",
    "error": "AI-Agent/Error",
}


class GmailClient:
    def __init__(self, credentials: Credentials) -> None:
        self.service = build("gmail", "v1", credentials=credentials, cache_discovery=False)
        self._label_ids: dict[str, str] = {}

    def ensure_labels(self) -> dict[str, str]:
        existing = self.service.users().labels().list(userId="me").execute().get("labels", [])
        by_name = {item["name"]: item["id"] for item in existing}
        for name in LABELS.values():
            if name not in by_name:
                created = (
                    self.service.users()
                    .labels()
                    .create(
                        userId="me",
                        body={
                            "name": name,
                            "labelListVisibility": "labelShow",
                            "messageListVisibility": "show",
                        },
                    )
                    .execute()
                )
                by_name[name] = created["id"]
        self._label_ids = by_name
        return by_name

    def unread_messages(self, *, lookback_days: int, max_messages: int) -> Iterable[EmailMessage]:
        page_token: str | None = None
        yielded = 0
        while True:
            result = (
                self.service.users()
                .messages()
                .list(
                    userId="me",
                    q=(
                        f"is:unread in:inbox newer_than:{lookback_days}d "
                        f'-label:"{LABELS["processed"]}"'
                    ),
                    maxResults=min(100, max_messages - yielded),
                    pageToken=page_token,
                )
                .execute()
            )
            for item in result.get("messages", []):
                raw = (
                    self.service.users()
                    .messages()
                    .get(userId="me", id=item["id"], format="raw")
                    .execute()
                )
                decoded = base64.urlsafe_b64decode(raw["raw"] + "===")
                mime = message_from_bytes(decoded, policy=default)
                yield parse_raw_message(item["id"], raw["threadId"], mime)
                yielded += 1
                if yielded >= max_messages:
                    return
            page_token = result.get("nextPageToken")
            if not page_token:
                return

    def apply_result(self, message_id: str, *, important: bool, draft_created: bool) -> None:
        labels = [
            self._label_ids[LABELS["important" if important else "low"]],
            self._label_ids[LABELS["processed"]],
        ]
        if draft_created:
            labels.append(self._label_ids[LABELS["draft"]])
        self.service.users().messages().modify(
            userId="me", id=message_id, body={"addLabelIds": labels, "removeLabelIds": ["UNREAD"]}
        ).execute()

    def create_draft(self, mime: MIMEEmail, thread_id: str) -> str:
        encoded = base64.urlsafe_b64encode(mime.as_bytes()).decode()
        result = (
            self.service.users()
            .drafts()
            .create(userId="me", body={"message": {"raw": encoded, "threadId": thread_id}})
            .execute()
        )
        return str(result["id"])

    def send_message(self, mime: MIMEEmail) -> str:
        encoded = base64.urlsafe_b64encode(mime.as_bytes()).decode()
        result = self.service.users().messages().send(userId="me", body={"raw": encoded}).execute()
        return str(result["id"])
