"""The Assistant (AI app) surface — the conversational entry point in Slack."""

from __future__ import annotations

import asyncio
from logging import Logger

from slack_bolt import App, Assistant, BoltContext, Say, SetStatus, SetSuggestedPrompts

from grant_copilot.agent.orchestrator import GrantAgent
from grant_copilot.domain.repositories import ProfileRepository
from grant_copilot.slack.blocks import grant_results

_MAX_MESSAGE_CHARS = 2000

_SUGGESTED_PROMPTS = [
    {
        "title": "Youth conservation",
        "message": "Find currently open grants for youth conservation programs.",
    },
    {
        "title": "Rural community health",
        "message": "Find currently open federal grants for rural community health programs.",
    },
]


def register(app: App, agent: GrantAgent, profile: ProfileRepository) -> None:
    """Attach the Assistant surface and its handlers to the Bolt app."""
    assistant = Assistant()
    assistant.thread_started(_greet)
    assistant.user_message(_make_reply(agent, profile))
    app.assistant(assistant)


def _greet(say: Say, set_suggested_prompts: SetSuggestedPrompts) -> None:
    say(
        "Describe your nonprofit's mission and I'll find profile-matched federal "
        "opportunities. Set your applicant type and focus areas once in the Home tab "
        "for a more precise pre-screen."
    )
    set_suggested_prompts(prompts=_SUGGESTED_PROMPTS)


def _make_reply(agent: GrantAgent, profile: ProfileRepository):
    def reply(
        payload: dict,
        context: BoltContext,
        say: Say,
        set_status: SetStatus,
        logger: Logger,
    ) -> None:
        try:
            request = (payload.get("text") or "").strip()[:_MAX_MESSAGE_CHARS]
            if not request:
                say("Tell me what your organization does or what kind of funding you need.")
                return
            set_status("Searching Grants.gov and checking source evidence…")
            org = profile.get(context.user_id)
            result = asyncio.run(agent.find(request, org))
            fallback_text = (
                "Here are the source-cited potential matches."
                if result.grants
                else "No currently actionable grants matched."
            )
            say(
                text=result.message or fallback_text,
                blocks=grant_results(result.message, result.grants),
            )
        except Exception as error:
            logger.exception("Grant search failed")
            say(_error_message(error))

    return reply


def _error_message(error: Exception) -> str:
    text = str(error).lower()
    if any(signal in text for signal in ("429", "rate limit", "capacity", "too many")):
        return "I'm handling a lot of requests right now — please try again in a few seconds."
    return "Something went wrong on my side. Please try again in a moment."
