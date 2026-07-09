"""Presentation formatting — escaping and human-readable dates."""

from __future__ import annotations

from datetime import date

from grant_copilot.slack.format import (
    date_label,
    deadline,
    mrkdwn_escape,
    mrkdwn_link,
)


def test_mrkdwn_escape_neutralizes_control_characters() -> None:
    assert mrkdwn_escape("a & b < c > d") == "a &amp; b &lt; c &gt; d"


def test_mrkdwn_escape_handles_none() -> None:
    assert mrkdwn_escape(None) == ""


def test_mrkdwn_link_encodes_url_delimiters() -> None:
    assert mrkdwn_link("https://x/<a>|b", "Title") == "<https://x/%3Ca%3E%7Cb|Title>"


def test_mrkdwn_link_keeps_label_from_breaking_syntax() -> None:
    # A pipe in the label would otherwise split link text from the URL.
    assert mrkdwn_link("https://x", "A|B") == "<https://x|A¦B>"


def test_date_label_is_platform_independent() -> None:
    assert date_label(date(2027, 3, 2)) == "Mar 2, 2027"


def test_deadline_reads_none_as_missing() -> None:
    assert deadline(None) == "No deadline listed"
    assert deadline(date(2027, 3, 2)) == "Closes Mar 2, 2027"
