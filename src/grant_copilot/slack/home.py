"""App Home view — the user's grant pipeline. Minimal: structure over decoration."""

from __future__ import annotations

import json
from datetime import date

from grant_copilot.domain.models import OrgProfile, PipelineItem, PipelineStatus
from grant_copilot.grants.taxonomy import (
    APPLICANT_TYPES,
    FOCUS_AREAS,
    applicant_label,
    focus_label,
)
from grant_copilot.slack.format import deadline, mrkdwn_escape, mrkdwn_link

_COLUMNS = [
    (PipelineStatus.TO_APPLY, "To apply"),
    (PipelineStatus.IN_PROGRESS, "In progress"),
    (PipelineStatus.SUBMITTED, "Submitted"),
]

_NEXT_STEP = {
    PipelineStatus.TO_APPLY: (PipelineStatus.IN_PROGRESS, "Start"),
    PipelineStatus.IN_PROGRESS: (PipelineStatus.SUBMITTED, "Mark submitted"),
}

_MAX_ITEMS_PER_COLUMN = 8
_GRANTS_GOV_NOTICE = (
    "This product uses the Grants.gov API but is not endorsed or certified by the "
    "U.S. Department of Health and Human Services."
)


def home_view(items: list[PipelineItem], profile: OrgProfile | None) -> dict:
    blocks: list[dict] = [
        {"type": "header", "text": {"type": "plain_text", "text": "Grant pipeline"}},
        _mission_block(profile),
    ]
    if profile:
        blocks.append(_profile_context(profile))
    blocks.append({"type": "divider"})
    if not items:
        blocks.append(
            _note(
                "No grants saved yet. Ask Grant Copilot in the Chat tab, then "
                "Save the ones that fit."
            )
        )
    else:
        for status, label in _COLUMNS:
            group = sorted(
                (item for item in items if item.status is status),
                key=_pipeline_sort_key,
            )
            blocks.append(
                {
                    "type": "header",
                    "text": {"type": "plain_text", "text": f"{label} ({len(group)})"},
                }
            )
            if not group:
                blocks.append(_note("Nothing here yet."))
                continue
            for item in group[:_MAX_ITEMS_PER_COLUMN]:
                blocks.extend(_item_blocks(item))
            if len(group) > _MAX_ITEMS_PER_COLUMN:
                blocks.append(
                    _note(
                        f"Showing the {_MAX_ITEMS_PER_COLUMN} nearest deadlines "
                        f"of {len(group)} grants in this stage."
                    )
                )
    blocks.extend(_trust_blocks())
    return {"type": "home", "blocks": blocks}


def profile_modal(profile: OrgProfile | None) -> dict:
    applicant_element = {
        "type": "static_select",
        "action_id": "value",
        "placeholder": {"type": "plain_text", "text": "Applicant type"},
        "options": [_option(label, code) for code, label in APPLICANT_TYPES],
    }
    if profile and profile.applicant_type:
        applicant_element["initial_option"] = _option(
            applicant_label(profile.applicant_type), profile.applicant_type
        )

    focus_element = {
        "type": "multi_static_select",
        "action_id": "value",
        "placeholder": {"type": "plain_text", "text": "Focus areas"},
        "options": [_option(label, code) for code, label in FOCUS_AREAS],
    }
    if profile and profile.focus_areas:
        focus_element["initial_options"] = [
            _option(focus_label(code), code) for code in profile.focus_areas
        ]

    mission_element = {
        "type": "plain_text_input",
        "action_id": "value",
        "multiline": True,
        "placeholder": {
            "type": "plain_text",
            "text": "e.g. After-school STEM programs in rural areas",
        },
    }
    if profile and profile.mission:
        mission_element["initial_value"] = profile.mission

    return {
        "type": "modal",
        "callback_id": "profile_modal",
        "title": {"type": "plain_text", "text": "Organization"},
        "submit": {"type": "plain_text", "text": "Save"},
        "close": {"type": "plain_text", "text": "Cancel"},
        "blocks": [
            {
                "type": "input",
                "block_id": "applicant",
                "optional": True,
                "label": {"type": "plain_text", "text": "Applicant type"},
                "element": applicant_element,
            },
            {
                "type": "input",
                "block_id": "focus",
                "optional": True,
                "label": {"type": "plain_text", "text": "Focus areas"},
                "element": focus_element,
            },
            {
                "type": "input",
                "block_id": "mission",
                "label": {"type": "plain_text", "text": "Mission"},
                "element": mission_element,
            },
        ],
    }


def drafting_modal(title: str) -> dict:
    return _summary_modal(
        [
            _section(f"*{mrkdwn_escape(title)}*"),
            {"type": "divider"},
            _section(
                "Creating a cautious draft starter from your mission and the official synopsis…"
            ),
            _note("This usually takes a few seconds."),
        ]
    )


def draft_modal(title: str, summary: str) -> dict:
    return _summary_modal(
        [
            _section(f"*{mrkdwn_escape(title)}*"),
            {"type": "divider"},
            _section(mrkdwn_escape(summary)),
            _note(
                "AI-generated starter — verify every claim against the official NOFO "
                "and replace every [NEEDS INPUT] before use."
            ),
        ]
    )


def _mission_block(profile: OrgProfile | None) -> dict:
    mission = profile.mission if profile else ""
    text = (
        f"*Organization* — {mrkdwn_escape(mission)}"
        if mission
        else "*Organization* — _not set_"
    )
    return {
        "type": "section",
        "text": {"type": "mrkdwn", "text": text},
        "accessory": {
            "type": "button",
            "text": {"type": "plain_text", "text": "Edit profile"},
            "action_id": "open_profile",
        },
    }


def _profile_context(profile: OrgProfile) -> dict:
    applicant = (
        applicant_label(profile.applicant_type)
        if profile.applicant_type
        else "Any applicant type"
    )
    focus = (
        ", ".join(focus_label(code) for code in profile.focus_areas)
        if profile.focus_areas
        else "Any focus"
    )
    return _note(
        mrkdwn_escape(
            f"Profile pre-screen: applicant type {applicant} · Focus: {focus}"
        )
    )


def _pipeline_sort_key(item: PipelineItem) -> tuple:
    """Put actionable deadlines first, then the most recently saved open-ended items."""
    return (
        item.grant.close_date is None,
        item.grant.close_date or date.max,
        -item.saved_at.timestamp(),
    )


def _trust_blocks() -> list[dict]:
    return [
        {"type": "divider"},
        _section(
            "*Data source & privacy*\n"
            f"{_GRANTS_GOV_NOTICE} Search and draft context is sent to Mistral AI. "
            "Always verify the official Notice of Funding Opportunity before applying."
        ),
        {
            "type": "actions",
            "elements": [
                {
                    **_button("Delete stored app data", "delete_user_data", "delete"),
                    "style": "danger",
                    "confirm": {
                        "title": {"type": "plain_text", "text": "Delete app data?"},
                        "text": {
                            "type": "mrkdwn",
                            "text": (
                                "This permanently deletes your profile and saved "
                                "grant pipeline."
                            ),
                        },
                        "confirm": {"type": "plain_text", "text": "Delete"},
                        "deny": {"type": "plain_text", "text": "Cancel"},
                    },
                }
            ],
        },
    ]


def _item_blocks(item: PipelineItem) -> list[dict]:
    grant = item.grant
    return [
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*{mrkdwn_link(grant.url, grant.title)}*",
            },
        },
        _note(f"{mrkdwn_escape(grant.agency)} · {deadline(grant.close_date)}"),
        {"type": "actions", "elements": _item_actions(item)},
    ]


def _item_actions(item: PipelineItem) -> list[dict]:
    elements: list[dict] = []
    step = _NEXT_STEP.get(item.status)
    if step:
        target, label = step
        elements.append(
            _button(
                label,
                "advance_status",
                json.dumps({"grant_id": item.grant.id, "status": target.value}),
            )
        )
    if item.status is not PipelineStatus.SUBMITTED:
        draft_value = json.dumps({"grant_id": item.grant.id, "title": item.grant.title})
        elements.append(_button("Draft starter", "draft_summary", draft_value))
    elements.append(_button("Remove", "remove_grant", item.grant.id))
    return elements


def _button(label: str, action_id: str, value: str) -> dict:
    return {
        "type": "button",
        "text": {"type": "plain_text", "text": label},
        "action_id": action_id,
        "value": value,
    }


def _option(label: str, value: str) -> dict:
    return {"text": {"type": "plain_text", "text": label}, "value": value}


def _summary_modal(blocks: list[dict]) -> dict:
    return {
        "type": "modal",
        "title": {"type": "plain_text", "text": "Draft starter"},
        "close": {"type": "plain_text", "text": "Close"},
        "blocks": blocks,
    }


def _section(text: str) -> dict:
    return {"type": "section", "text": {"type": "mrkdwn", "text": text}}


def _note(text: str) -> dict:
    return {"type": "context", "elements": [{"type": "mrkdwn", "text": text}]}
