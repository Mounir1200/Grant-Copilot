"""Interactive handlers — saving grants, moving pipeline status, editing profile."""

from __future__ import annotations

import asyncio
import json
from logging import Logger

from slack_bolt import Ack, App, Respond
from slack_sdk import WebClient

from grant_copilot.agent.drafter import Drafter
from grant_copilot.domain.models import Grant, OrgProfile, PipelineStatus
from grant_copilot.domain.repositories import PipelineRepository, ProfileRepository
from grant_copilot.grants.taxonomy import APPLICANT_CODES, FOCUS_CODES
from grant_copilot.slack.format import mrkdwn_escape
from grant_copilot.slack.home import (
    draft_modal,
    drafting_modal,
    home_view,
    profile_modal,
)


def register(
    app: App, pipeline: PipelineRepository, profile: ProfileRepository, drafter: Drafter
) -> None:
    """Wire every interactive component to its handler."""
    app.event("app_home_opened")(_publish_home_handler(pipeline, profile))
    app.action("save_grant")(_save_handler(pipeline))
    app.action("advance_status")(_advance_handler(pipeline, profile))
    app.action("remove_grant")(_remove_handler(pipeline, profile))
    app.action("draft_summary")(_draft_handler(drafter, profile))
    app.action("open_profile")(_open_profile_handler(profile))
    app.view("profile_modal")(_save_profile_handler(pipeline, profile))


def _publish_home(
    client: WebClient,
    user_id: str,
    pipeline: PipelineRepository,
    profile: ProfileRepository,
) -> None:
    client.views_publish(
        user_id=user_id,
        view=home_view(pipeline.list(user_id), profile.get(user_id)),
    )


def _publish_home_handler(pipeline: PipelineRepository, profile: ProfileRepository):
    def handler(event: dict, client: WebClient) -> None:
        _publish_home(client, event["user"], pipeline, profile)

    return handler


def _save_handler(pipeline: PipelineRepository):
    def handler(ack: Ack, body: dict, respond: Respond, logger: Logger) -> None:
        ack()
        grant = Grant.from_dict(json.loads(body["actions"][0]["value"]))
        pipeline.save(body["user"]["id"], grant)
        respond(
            response_type="ephemeral",
            replace_original=False,
            text=f"Saved *{mrkdwn_escape(grant.title)}* — open the *Home* tab to track it.",
        )

    return handler


def _advance_handler(pipeline: PipelineRepository, profile: ProfileRepository):
    def handler(ack: Ack, body: dict, client: WebClient) -> None:
        ack()
        move = json.loads(body["actions"][0]["value"])
        user_id = body["user"]["id"]
        pipeline.set_status(user_id, move["grant_id"], PipelineStatus(move["status"]))
        _publish_home(client, user_id, pipeline, profile)

    return handler


def _remove_handler(pipeline: PipelineRepository, profile: ProfileRepository):
    def handler(ack: Ack, body: dict, client: WebClient) -> None:
        ack()
        user_id = body["user"]["id"]
        pipeline.remove(user_id, body["actions"][0]["value"])
        _publish_home(client, user_id, pipeline, profile)

    return handler


def _open_profile_handler(profile: ProfileRepository):
    def handler(ack: Ack, body: dict, client: WebClient) -> None:
        ack()
        user_id = body["user"]["id"]
        client.views_open(
            trigger_id=body["trigger_id"],
            view=profile_modal(profile.get(user_id)),
        )

    return handler


def _save_profile_handler(pipeline: PipelineRepository, profile: ProfileRepository):
    def handler(ack: Ack, body: dict, view: dict, client: WebClient) -> None:
        ack()
        user_id = body["user"]["id"]
        values = view["state"]["values"]
        applicant = (values["applicant"]["value"].get("selected_option") or {}).get(
            "value", ""
        )
        # Re-validate against the taxonomy: Slack only offers valid options, but
        # never trust the payload — drop anything outside the known code sets.
        if applicant not in APPLICANT_CODES:
            applicant = ""
        focus = tuple(
            option["value"]
            for option in values["focus"]["value"].get("selected_options", [])
            if option["value"] in FOCUS_CODES
        )
        mission = values["mission"]["value"]["value"] or ""
        profile.save(
            user_id,
            OrgProfile(
                mission=mission,
                applicant_type=applicant,
                focus_areas=focus,
            ),
        )
        _publish_home(client, user_id, pipeline, profile)

    return handler


def _draft_handler(drafter: Drafter, profile: ProfileRepository):
    def handler(ack: Ack, body: dict, client: WebClient, logger: Logger) -> None:
        ack()
        request = json.loads(body["actions"][0]["value"])
        user_id = body["user"]["id"]
        opened = client.views_open(
            trigger_id=body["trigger_id"], view=drafting_modal(request["title"])
        )
        view_id = opened["view"]["id"]
        try:
            org = profile.get(user_id)
            title, summary = asyncio.run(
                drafter.draft_summary(request["grant_id"], org.mission if org else None)
            )
            client.views_update(view_id=view_id, view=draft_modal(title, summary))
        except Exception:
            logger.exception("Draft failed")
            client.views_update(
                view_id=view_id,
                view=draft_modal(
                    request["title"],
                    "Something went wrong. Please try again in a moment.",
                ),
            )

    return handler
