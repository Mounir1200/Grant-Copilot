"""Smoke test: connect to the grants MCP server over stdio and call a tool.

Proves the MCP client <-> server round-trip (the required-technology pillar)
before the orchestrator relies on it — no API key needed.

    uv run python scripts/spike_mcp_client.py "clean water"
"""

from __future__ import annotations

import asyncio
import sys

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

_SERVER = StdioServerParameters(
    command=sys.executable, args=["-m", "grant_copilot.mcp_server"]
)


async def main() -> None:
    keyword = sys.argv[1] if len(sys.argv) > 1 else "education"
    async with stdio_client(_SERVER) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            listing = await session.list_tools()
            for tool in listing.tools:
                print("tool:", tool.name, "| schema:", tool.inputSchema)
            result = await session.call_tool(
                "search_grants", {"keyword": keyword, "limit": 3}
            )
            for block in result.content:
                if getattr(block, "type", None) == "text":
                    print("result:", block.text[:600])


if __name__ == "__main__":
    asyncio.run(main())
