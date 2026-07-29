from __future__ import annotations

from datetime import UTC, datetime

from gmail_agent.digest import render_digest
from gmail_agent.models import Analysis, Category, Classification


def test_digest_escapes_user_controlled_html(make_message) -> None:
    message = make_message("<script>alert(1)</script>", subject="<b>unsafe</b>")
    result = Analysis(
        classification=Classification.IMPORTANT,
        category=Category.SJSU,
        confidence=1,
        reason="<img src=x>",
        summary="<script>bad</script>",
    )
    mime = render_digest(
        [(message, result, False)],
        "source@example.com",
        "digest@example.com",
        datetime.now(UTC),
    )
    html_part = mime.get_payload()[1].get_content()
    assert "<script>" not in html_part
    assert "&lt;script&gt;" in html_part
