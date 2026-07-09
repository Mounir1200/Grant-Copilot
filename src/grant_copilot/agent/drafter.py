"""Drafts a tailored 'Project Summary' from a grant's detail and the mission.

Grounds the draft in the opportunity's own text (fetched via the MCP get_grant
tool) so Mistral does not invent requirements.
"""

from __future__ import annotations

import asyncio
import json

from mistralai.client import Mistral

from grant_copilot.agent.mcp_session import mcp_session, tool_text

_DEFAULT_MODEL = "mistral-small-latest"
_MAX_DESCRIPTION_CHARS = 2000
_SYSTEM_PROMPT = (
    "You write project summaries for nonprofit grant applications. Produce a "
    "single confident paragraph of 120-160 words, tailored to the funding "
    "opportunity and the nonprofit's mission. No preamble, no bullet points."
)


class Drafter:
    """Turns a saved grant into a first-draft project summary."""

    def __init__(self, mistral: Mistral, model: str = _DEFAULT_MODEL) -> None:
        self._mistral = mistral
        self._model = model

    async def draft_summary(
        self, grant_id: str, mission: str | None
    ) -> tuple[str, str]:
        async with mcp_session() as session:
            result = await session.call_tool("get_grant", {"opportunity_id": grant_id})
        detail = json.loads(tool_text(result))
        reply = await asyncio.to_thread(
            self._mistral.chat.complete,
            model=self._model,
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": _prompt(detail, mission)},
            ],
        )
        return detail.get("title", "Project summary"), (
            reply.choices[0].message.content or ""
        )


def _prompt(detail: dict, mission: str | None) -> str:
    description = detail.get("description", "")[:_MAX_DESCRIPTION_CHARS]
    return (
        f"Funding opportunity: {detail.get('title')} ({detail.get('agency')}).\n"
        f"Opportunity description: {description}\n\n"
        f"Our nonprofit's mission: {mission or 'a nonprofit applying to this grant'}\n\n"
        "Write our project summary for this application."
    )
