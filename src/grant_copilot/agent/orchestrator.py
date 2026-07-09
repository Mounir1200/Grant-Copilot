"""Mistral orchestrator wired to the grants MCP server.

Two steps, each with one responsibility:
  1. search  — a bounded tool-use loop that gathers matching grants.
  2. curate  — a structured pass that writes a calm summary and a one-line
               relevance reason for the strongest matches.
"""

from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass

from mcp import ClientSession
from mistralai.client import Mistral

from grant_copilot.agent.mcp_session import mcp_session, tool_text
from grant_copilot.domain.models import OrgProfile

_DEFAULT_MODEL = "mistral-small-latest"
_MAX_TOOL_ROUNDS = 3

_SEARCH_PROMPT = (
    "You are Grant Copilot. Use the search_grants tool to find U.S. federal "
    "grants that match the user's mission and request. Choose the best keyword "
    "and call the tool. Do not invent grants."
)
_CURATE_PROMPT = (
    "You are Grant Copilot, a precise, understated assistant for nonprofits. "
    'Return ONLY JSON: {"summary": string, "picks": [{"id": string, "reason": string}]}. '
    "'summary' is one calm, concise sentence framing the matches — no hype, no "
    "exclamation marks. 'picks' lists up to 5 grants most relevant to the mission "
    "and request, most relevant first; 'reason' is a short phrase under 10 words. "
    "Use only grant ids from the provided list."
)


@dataclass(frozen=True, slots=True)
class AgentResult:
    """The agent's answer: a short summary plus the grants it surfaced."""

    message: str
    grants: list[dict]


class GrantAgent:
    """Searches the grants MCP server, then curates the results for display."""

    def __init__(self, mistral: Mistral, model: str = _DEFAULT_MODEL) -> None:
        self._mistral = mistral
        self._model = model

    async def find(
        self, request: str, profile: OrgProfile | None = None
    ) -> AgentResult:
        async with mcp_session() as session:
            tools = _to_mistral_tools(await session.list_tools())
            grants = await self._search(session, tools, request, profile)
        if not grants:
            return AgentResult(message="", grants=[])
        return await self._curate(request, profile.mission if profile else None, grants)

    async def _search(
        self,
        session: ClientSession,
        tools: list[dict],
        request: str,
        profile: OrgProfile | None,
    ) -> list[dict]:
        mission = profile.mission if profile else None
        user_content = (
            request
            if not mission
            else f"Nonprofit mission: {mission}\n\nRequest: {request}"
        )
        eligibilities = (
            [profile.applicant_type] if profile and profile.applicant_type else []
        )
        funding_categories = list(profile.focus_areas) if profile else []
        messages: list = [
            {"role": "system", "content": _SEARCH_PROMPT},
            {"role": "user", "content": user_content},
        ]
        grants: list[dict] = []

        for _ in range(_MAX_TOOL_ROUNDS):
            reply = await asyncio.to_thread(
                self._mistral.chat.complete,
                model=self._model,
                messages=messages,
                tools=tools,
                tool_choice="auto",
            )
            answer = reply.choices[0].message
            messages.append(answer)
            if not answer.tool_calls:
                break
            for call in answer.tool_calls:
                args = json.loads(call.function.arguments or "{}")
                if call.function.name == "search_grants":
                    args["eligibilities"] = eligibilities
                    args["funding_categories"] = funding_categories
                result = await session.call_tool(call.function.name, args)
                text = tool_text(result)
                messages.append(
                    {
                        "role": "tool",
                        "name": call.function.name,
                        "tool_call_id": call.id,
                        "content": text,
                    }
                )
                if call.function.name == "search_grants":
                    grants = _merge_grants(grants, json.loads(text).get("grants", []))
        return grants

    async def _curate(
        self, request: str, mission: str | None, grants: list[dict]
    ) -> AgentResult:
        catalog = [
            {"id": g["id"], "title": g["title"], "agency": g["agency"]} for g in grants
        ]
        reply = await asyncio.to_thread(
            self._mistral.chat.complete,
            model=self._model,
            messages=[
                {"role": "system", "content": _CURATE_PROMPT},
                {
                    "role": "user",
                    "content": f"Mission: {mission or 'not specified'}\nRequest: {request}\nGrants:\n{json.dumps(catalog)}",
                },
            ],
            response_format={"type": "json_object"},
        )
        return _build_result(reply.choices[0].message.content, grants)


def _build_result(content: str | None, grants: list[dict]) -> AgentResult:
    by_id = {grant["id"]: grant for grant in grants}
    try:
        data = json.loads(content or "{}")
    except json.JSONDecodeError:
        data = {}
    picks = [
        p for p in data.get("picks", []) if isinstance(p, dict) and p.get("id") in by_id
    ]
    chosen = [{**by_id[pick["id"]], "reason": pick.get("reason", "")} for pick in picks]
    return AgentResult(message=data.get("summary", ""), grants=chosen or grants)


def _to_mistral_tools(listing) -> list[dict]:
    tools = []
    for tool in listing.tools:
        schema = tool.inputSchema
        if tool.name == "search_grants":
            schema = {
                "type": "object",
                "properties": {
                    "keyword": {
                        "type": "string",
                        "description": "search keyword",
                    }
                },
                "required": ["keyword"],
            }
        tools.append(
            {
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description or "",
                    "parameters": schema,
                },
            }
        )
    return tools


def _merge_grants(existing: list[dict], found: list[dict]) -> list[dict]:
    seen = {grant["id"] for grant in existing}
    return existing + [grant for grant in found if grant["id"] not in seen]
