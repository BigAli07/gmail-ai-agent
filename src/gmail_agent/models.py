from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class Classification(StrEnum):
    IMPORTANT = "IMPORTANT"
    LOW_PRIORITY = "LOW_PRIORITY"


class Category(StrEnum):
    SJSU = "SJSU"
    AI_NEWS = "AI_NEWS"
    INTERNSHIP = "INTERNSHIP"
    HACKATHON = "HACKATHON"
    SCHOLARSHIP = "SCHOLARSHIP"
    OTHER_IMPORTANT_NEWS = "OTHER_IMPORTANT_NEWS"
    LOW_PRIORITY = "LOW_PRIORITY"


class EmailMessage(BaseModel):
    id: str
    thread_id: str
    sender: str
    sender_email: str
    subject: str
    received_at: datetime
    plain_body: str = ""
    html_body: str = ""
    attachment_filenames: list[str] = Field(default_factory=list)
    message_id_header: str | None = None
    references: str | None = None
    list_id: str | None = None
    auto_submitted: str | None = None
    links: list[str] = Field(default_factory=list)

    @property
    def classification_text(self) -> str:
        return "\n".join(
            [self.sender, self.subject, self.plain_body, self.html_body, *self.attachment_filenames]
        )[:30_000]


class Analysis(BaseModel):
    classification: Classification
    category: Category
    confidence: float = Field(ge=0, le=1)
    reason: str
    summary: str = ""
    deadlines: list[str] = Field(default_factory=list)
    action_items: list[str] = Field(default_factory=list)
    useful_links: list[str] = Field(default_factory=list)
    should_create_draft: bool = False
