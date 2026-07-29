from __future__ import annotations

import logging
from collections.abc import Iterable
from datetime import UTC, datetime
from email.message import EmailMessage as MIMEEmail
from typing import Protocol

from .classifier import Analyzer
from .config import Settings
from .digest import render_digest
from .drafts import render_draft
from .models import Analysis, Classification, EmailMessage
from .state import StateRepository

logger = logging.getLogger(__name__)


class Mailbox(Protocol):
    def ensure_labels(self) -> dict[str, str]: ...
    def unread_messages(
        self, *, lookback_days: int, max_messages: int
    ) -> Iterable[EmailMessage]: ...
    def apply_result(self, message_id: str, *, important: bool, draft_created: bool) -> None: ...
    def create_draft(self, mime: MIMEEmail, thread_id: str) -> str: ...
    def send_message(self, mime: MIMEEmail) -> str: ...


class GmailAgent:
    def __init__(
        self,
        settings: Settings,
        gmail: Mailbox,
        analyzer: Analyzer,
        state: StateRepository,
    ) -> None:
        self.settings = settings
        self.gmail = gmail
        self.analyzer = analyzer
        self.state = state

    def run_once(self) -> dict[str, int]:
        if not self.settings.dry_run:
            self.gmail.ensure_labels()
        important: list[tuple[EmailMessage, Analysis, bool]] = []
        counts = {"classified": 0, "important": 0, "low_priority": 0, "drafts": 0}
        messages = self.gmail.unread_messages(
            lookback_days=self.settings.gmail_lookback_days,
            max_messages=self.settings.max_messages_per_run,
        )
        for message in messages:
            if self.state.exists(message.id):
                continue
            analysis = self.analyzer.analyze(message)
            counts["classified"] += 1
            is_important = analysis.classification == Classification.IMPORTANT
            counts["important" if is_important else "low_priority"] += 1
            draft_created = self.state.draft_exists(message.id)
            draft_id: str | None = None
            if analysis.should_create_draft and not draft_created:
                draft = render_draft(message, str(self.settings.gmail_account_email))
                if self.settings.dry_run:
                    logger.info("dry_run_draft_preview", extra={"message_id": message.id})
                else:
                    draft_id = self.gmail.create_draft(draft, message.thread_id)
                    draft_created = True
                    counts["drafts"] += 1
            if self.settings.dry_run:
                logger.info(
                    "dry_run_classification",
                    extra={
                        "message_id": message.id,
                        "classification": analysis.classification.value,
                        "reason": analysis.reason,
                    },
                )
            elif is_important:
                self.state.stage(message.id, analysis, draft_id)
            else:
                self.state.stage(message.id, analysis, draft_id)
                self.gmail.apply_result(message.id, important=False, draft_created=draft_created)
                self.state.complete(message.id)
            if is_important:
                important.append((message, analysis, draft_created))
        if important:
            digest = render_digest(
                important,
                str(self.settings.gmail_account_email),
                str(self.settings.digest_recipient_email),
                datetime.now(UTC),
            )
            if self.settings.dry_run:
                logger.info(
                    "dry_run_digest_preview",
                    extra={"messages": len(important), "subject": digest["Subject"]},
                )
            else:
                digest_id = self.gmail.send_message(digest)
                for message, _analysis, draft_created in important:
                    self.gmail.apply_result(message.id, important=True, draft_created=draft_created)
                    self.state.complete(message.id, digest_id)
        return counts
