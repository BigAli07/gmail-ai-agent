from __future__ import annotations

from pathlib import Path
from unittest.mock import Mock

import pytest

from gmail_agent.agent import GmailAgent
from gmail_agent.config import Settings
from gmail_agent.models import Analysis, Category, Classification
from gmail_agent.state import StateRepository


def settings(tmp_path: Path, *, dry_run: bool = False) -> Settings:
    return Settings(
        gmail_account_email="source@example.com",
        digest_recipient_email="digest@example.com",
        database_path=tmp_path / "state.db",
        dry_run=dry_run,
    )


def analysis(classification: Classification, *, draft: bool = False) -> Analysis:
    return Analysis(
        classification=classification,
        category=(
            Category.INTERNSHIP
            if classification == Classification.IMPORTANT
            else Category.LOW_PRIORITY
        ),
        confidence=0.9,
        reason="test",
        summary="summary",
        should_create_draft=draft,
    )


def test_duplicate_message_not_processed_twice(tmp_path, make_message) -> None:
    repo = StateRepository(tmp_path / "state.db")
    msg = make_message("promo")
    repo.stage(msg.id, analysis(Classification.LOW_PRIORITY))
    repo.complete(msg.id)
    gmail = Mock()
    gmail.unread_messages.return_value = [msg]
    analyzer = Mock()
    result = GmailAgent(settings(tmp_path), gmail, analyzer, repo).run_once()
    assert result["classified"] == 0
    analyzer.analyze.assert_not_called()


def test_empty_important_set_sends_no_digest(tmp_path, make_message) -> None:
    gmail = Mock()
    gmail.unread_messages.return_value = [make_message("promo")]
    analyzer = Mock()
    analyzer.analyze.return_value = analysis(Classification.LOW_PRIORITY)
    GmailAgent(settings(tmp_path), gmail, analyzer, StateRepository(tmp_path / "s.db")).run_once()
    gmail.send_message.assert_not_called()
    gmail.apply_result.assert_called_once()


def test_digest_failure_leaves_important_unprocessed(tmp_path, make_message) -> None:
    msg = make_message("internship")
    gmail = Mock()
    gmail.unread_messages.return_value = [msg]
    gmail.send_message.side_effect = RuntimeError("network")
    analyzer = Mock()
    analyzer.analyze.return_value = analysis(Classification.IMPORTANT)
    repo = StateRepository(tmp_path / "s.db")
    with pytest.raises(RuntimeError):
        GmailAgent(settings(tmp_path), gmail, analyzer, repo).run_once()
    assert not repo.exists(msg.id)
    gmail.apply_result.assert_not_called()


def test_successful_important_processing_labels_and_marks_read(tmp_path, make_message) -> None:
    gmail = Mock()
    gmail.unread_messages.return_value = [make_message("internship")]
    gmail.send_message.return_value = "digest-1"
    analyzer = Mock()
    analyzer.analyze.return_value = analysis(Classification.IMPORTANT)
    GmailAgent(settings(tmp_path), gmail, analyzer, StateRepository(tmp_path / "s.db")).run_once()
    gmail.apply_result.assert_called_once_with("m1", important=True, draft_created=False)


def test_dry_run_does_not_mutate_gmail_or_state(tmp_path, make_message) -> None:
    gmail = Mock()
    gmail.unread_messages.return_value = [make_message("internship")]
    analyzer = Mock()
    analyzer.analyze.return_value = analysis(Classification.IMPORTANT, draft=True)
    repo = StateRepository(tmp_path / "s.db")
    GmailAgent(settings(tmp_path, dry_run=True), gmail, analyzer, repo).run_once()
    gmail.ensure_labels.assert_not_called()
    gmail.create_draft.assert_not_called()
    gmail.send_message.assert_not_called()
    gmail.apply_result.assert_not_called()
    assert not repo.exists("m1")


def test_duplicate_draft_is_not_created_on_digest_retry(tmp_path, make_message) -> None:
    msg = make_message("please reply to internship")
    gmail = Mock()
    gmail.unread_messages.return_value = [msg]
    gmail.create_draft.return_value = "draft-1"
    gmail.send_message.side_effect = [RuntimeError("fail"), "digest-1"]
    analyzer = Mock()
    analyzer.analyze.return_value = analysis(Classification.IMPORTANT, draft=True)
    repo = StateRepository(tmp_path / "s.db")
    agent = GmailAgent(settings(tmp_path), gmail, analyzer, repo)
    with pytest.raises(RuntimeError):
        agent.run_once()
    agent.run_once()
    assert gmail.create_draft.call_count == 1
