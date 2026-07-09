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
        "title": "Find education grants",
        "message": "Find grants for youth education programs.",
    },
    {
        "title": "Climate funding",
        "message": "Show climate resilience funding for nonprofits.",
    },
]


def register(app: App, agent: GrantAgent, profile: ProfileRepository) -> None:
    """Attach the Assistant surface and its handlers to the Bolt app."""
    assistant = Assistant()
    assistant.thread_started(_greet)
    assistant.user_message(_make_reply(agent, profile))
    app.assistant(assistant)


def _greet(say: Say, set_suggested_prompts: SetSuggestedPrompts) -> None:
    say("Describe your nonprofit's mission and I'll find grants that fit.")
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
            set_status("Searching grants…")
            org = profile.get(context.user_id)
            request = (payload.get("text") or "")[:_MAX_MESSAGE_CHARS]
            result = asyncio.run(agent.find(request, org))
            say(
                text=result.message or "Here are some grants.",
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
