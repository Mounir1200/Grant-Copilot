"""Smoke test for Mistral function calling (the tool-use loop the agent relies on).

Defines one dummy tool, lets the model call it, returns the result, and prints
the final answer. Validates the loop before the MCP tools are wired in Phase 1.

    uv run python scripts/spike_mistral_tools.py   # needs MISTRAL_API_KEY
"""

from __future__ import annotations

import json
import os

from dotenv import load_dotenv
from mistralai.client import Mistral

MODEL = "mistral-small-latest"

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_grant_count",
            "description": "Return how many open grants match a topic.",
            "parameters": {
                "type": "object",
                "properties": {"topic": {"type": "string"}},
                "required": ["topic"],
            },
        },
    }
]


def get_grant_count(topic: str) -> int:
    """Dummy data source — replaced by the MCP server in Phase 1."""
    return 42


def main() -> None:
    load_dotenv()
    client = Mistral(api_key=os.environ["MISTRAL_API_KEY"])
    messages: list = [
        {"role": "user", "content": "How many open grants are there for clean water?"}
    ]

    first = client.chat.complete(
        model=MODEL, messages=messages, tools=TOOLS, tool_choice="auto"
    )
    answer = first.choices[0].message
    messages.append(answer)

    for call in answer.tool_calls or []:
        arguments = json.loads(call.function.arguments)
        result = get_grant_count(**arguments)
        messages.append(
            {
                "role": "tool",
                "name": call.function.name,
                "tool_call_id": call.id,
                "content": str(result),
            }
        )

    final = client.chat.complete(model=MODEL, messages=messages, tools=TOOLS)
    print(final.choices[0].message.content)


if __name__ == "__main__":
    main()
