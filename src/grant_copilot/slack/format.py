"""Shared presentation formatting — human-readable dates for Slack surfaces."""

from __future__ import annotations

from datetime import date


def mrkdwn_escape(text: object) -> str:
    """Escape Slack mrkdwn control characters in untrusted text."""
    return (
        str(text or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    )


def mrkdwn_link(url: str, label: str) -> str:
    """Render a Slack link while keeping the label from breaking mrkdwn syntax."""
    safe_url = (
        str(url or "")
        .strip()
        .replace("<", "%3C")
        .replace(">", "%3E")
        .replace("|", "%7C")
    )
    safe_label = mrkdwn_escape(str(label or "").replace("|", "¦"))
    return f"<{safe_url}|{safe_label}>"


def date_label(value: date) -> str:
    """Render a date as 'Mar 2, 2027' (portable, no platform-specific strftime)."""
    return f"{value.strftime('%b')} {value.day}, {value.year}"


def deadline(close_date: date | None) -> str:
    return (
        "No deadline listed"
        if close_date is None
        else f"Closes {date_label(close_date)}"
    )
