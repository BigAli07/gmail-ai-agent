from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from .models import Analysis


class StateRepository:
    def __init__(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(path)
        self.connection.row_factory = sqlite3.Row
        self.connection.execute("PRAGMA journal_mode=WAL")
        self.connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS messages (
              message_id TEXT PRIMARY KEY,
              classification TEXT NOT NULL,
              category TEXT NOT NULL,
              reason TEXT NOT NULL,
              draft_id TEXT,
              digest_id TEXT,
              processed INTEGER NOT NULL DEFAULT 0,
              created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            """
        )

    @contextmanager
    def transaction(self) -> Iterator[sqlite3.Connection]:
        with self.connection:
            yield self.connection

    def exists(self, message_id: str) -> bool:
        row = self.connection.execute(
            "SELECT processed FROM messages WHERE message_id = ?", (message_id,)
        ).fetchone()
        return bool(row and row["processed"])

    def draft_exists(self, message_id: str) -> bool:
        row = self.connection.execute(
            "SELECT draft_id FROM messages WHERE message_id = ?", (message_id,)
        ).fetchone()
        return bool(row and row["draft_id"])

    def stage(self, message_id: str, analysis: Analysis, draft_id: str | None = None) -> None:
        with self.connection:
            self.connection.execute(
                """INSERT INTO messages(message_id, classification, category, reason, draft_id)
                   VALUES (?, ?, ?, ?, ?)
                   ON CONFLICT(message_id) DO UPDATE SET
                     classification=excluded.classification, category=excluded.category,
                     reason=excluded.reason,
                     draft_id=COALESCE(messages.draft_id, excluded.draft_id)""",
                (
                    message_id,
                    analysis.classification.value,
                    analysis.category.value,
                    analysis.reason,
                    draft_id,
                ),
            )

    def complete(self, message_id: str, digest_id: str | None = None) -> None:
        with self.connection:
            self.connection.execute(
                """UPDATE messages SET processed=1,
                   digest_id=COALESCE(digest_id, ?) WHERE message_id=?""",
                (digest_id, message_id),
            )
