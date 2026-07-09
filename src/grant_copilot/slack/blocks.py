"""Block Kit rendering for grant results — minimal, hierarchy over decoration."""

from __future__ import annotations

import json
from datetime import date

from grant_copilot.slack.format import deadline, mrkdwn_escape, mrkdwn_link

_MAX_CARDS = 5
# Only the fields Grant.from_dict reads. Keeping the button value minimal holds
# it under Slack's 2000-char limit and shrinks the round-tripped payload.
_SAVE_FIELDS = ("id", "title", "agency", "close_date", "url")


def grant_results(message: str, grants: list[dict]) -> list[dict]:
    """Render a calm summary followed by one savable card per grant."""
    if not grants:
        return [
            _section("No grants matched — try describing your mission differently.")
        ]

    blocks: list[dict] = []
    if message:
        blocks.append(_section(mrkdwn_escape(message)))
    for grant in grants[:_MAX_CARDS]:
        if blocks:
            blocks.append({"type": "divider"})
        blocks.extend(_card(grant))
    return blocks


def _card(grant: dict) -> list[dict]:
    close = date.fromisoformat(grant["close_date"]) if grant["close_date"] else None
    blocks = [
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*{mrkdwn_link(grant['url'], grant['title'])}*",
            },
            "accessory": {
                "type": "button",
                "text": {"type": "plain_text", "text": "Save"},
                "action_id": "save_grant",
                "value": _save_value(grant),
            },
        },
        _meta(f"{mrkdwn_escape(grant['agency'])} · {deadline(close)}"),
    ]
    if grant.get("reason"):
        blocks.append(_meta(mrkdwn_escape(grant["reason"])))
    return blocks


def _save_value(grant: dict) -> str:
    return json.dumps({field: grant[field] for field in _SAVE_FIELDS})


def _section(text: str) -> dict:
    return {"type": "section", "text": {"type": "mrkdwn", "text": text}}


def _meta(text: str) -> dict:
    return {"type": "context", "elements": [{"type": "mrkdwn", "text": text}]}
