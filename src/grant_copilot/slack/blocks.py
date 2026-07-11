"""Block Kit rendering for grant results — minimal, hierarchy over decoration."""

from __future__ import annotations

import json
from datetime import date

from grant_copilot.slack.format import deadline, mrkdwn_escape, mrkdwn_link

_MAX_CARDS = 5
_SOURCE_NOTICE = (
    "This product uses the Grants.gov API but is not endorsed or certified by the "
    "U.S. Department of Health and Human Services."
)
# Only the fields Grant.from_dict reads. Keeping the button value minimal holds
# it under Slack's 2000-char limit and shrinks the round-tripped payload.
_SAVE_FIELDS = ("id", "title", "agency", "close_date", "url")


def grant_results(message: str, grants: list[dict]) -> list[dict]:
    """Render a calm summary followed by one savable card per grant."""
    if not grants:
        return [
            _section(
                "No currently actionable grants matched. Try a broader description "
                "or adjust your organization profile."
            ),
            _meta(_SOURCE_NOTICE),
        ]

    blocks: list[dict] = []
    if message:
        blocks.append(_section(mrkdwn_escape(message)))
    for grant in grants[:_MAX_CARDS]:
        if blocks:
            blocks.append({"type": "divider"})
        blocks.extend(_card(grant))
    blocks.append({"type": "divider"})
    blocks.append(
        _meta(
            f"{_SOURCE_NOTICE} Profile matching is a pre-screen, not an eligibility determination."
        )
    )
    return blocks


def _card(grant: dict) -> list[dict]:
    close = date.fromisoformat(grant["close_date"]) if grant["close_date"] else None
    status = str(grant.get("status") or "").strip().lower()
    status_label = "Open" if status == "posted" else status.title()
    metadata = " · ".join(
        part
        for part in (status_label, mrkdwn_escape(grant["agency"]), deadline(close))
        if part
    )
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
        _meta(metadata),
    ]
    reason = mrkdwn_escape(grant.get("reason"))
    evidence = mrkdwn_escape(grant.get("evidence"))
    if reason or evidence:
        fit_lines = []
        if reason:
            fit_lines.append(f"*AI rationale — verify against the evidence:* {reason}")
        if evidence:
            fit_lines.append(f"*Source evidence:* “{evidence}”")
        blocks.append(_section("\n".join(fit_lines)))
    return blocks


def _save_value(grant: dict) -> str:
    return json.dumps({field: grant[field] for field in _SAVE_FIELDS})


def _section(text: str) -> dict:
    return {"type": "section", "text": {"type": "mrkdwn", "text": text}}


def _meta(text: str) -> dict:
    return {"type": "context", "elements": [{"type": "mrkdwn", "text": text}]}
