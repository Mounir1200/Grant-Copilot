"""Shared MCP client access — one grants MCP server, spawned over stdio.

Both the search orchestrator and the drafter connect through here, so the MCP
transport details live in a single place (DRY).
"""

from __future__ import annotations

import sys
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

_SERVER = StdioServerParameters(
    command=sys.executable, args=["-m", "grant_copilot.mcp_server"]
)


@asynccontextmanager
async def mcp_session() -> AsyncIterator[ClientSession]:
    """Spawn the grants MCP server and yield an initialized client session."""
    async with stdio_client(_SERVER) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            yield session


def tool_text(result) -> str:
    """Concatenate the text content blocks of an MCP tool result."""
    return "".join(
        block.text for block in result.content if getattr(block, "type", None) == "text"
    )
