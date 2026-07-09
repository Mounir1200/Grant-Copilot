"""MCP server exposing grants.gov funding opportunities as agent tools.

Runs as a standalone process over stdio; the agent connects to it as an MCP
client. This is the project's MCP integration — the required-technology pillar.

    uv run python -m grant_copilot.mcp_server
"""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from grant_copilot.grants.client import GrantsGovClient
from grant_copilot.grants.mapper import to_grant, to_grant_detail

mcp = FastMCP("grant-copilot")
_grants = GrantsGovClient()
_DEFAULT_SEARCH_LIMIT = 10
_MAX_SEARCH_LIMIT = 25


@mcp.tool()
def search_grants(
    keyword: str,
    funding_categories: list[str] | None = None,
    eligibilities: list[str] | None = None,
    limit: int = 10,
) -> dict:
    """Search open U.S. federal funding opportunities by keyword and facets.

    funding_categories and eligibilities are grants.gov codes; passing them
    restricts results to grants the applicant actually qualifies for.
    """
    term = str(keyword or "").strip()
    if not term:
        return {"grants": []}
    records = _grants.search(
        term,
        rows=_bounded_limit(limit),
        eligibilities=_pipe(eligibilities),
        funding_categories=_pipe(funding_categories),
    )
    return {"grants": [to_grant(record).to_dict() for record in records]}


@mcp.tool()
def get_grant(opportunity_id: str) -> dict:
    """Fetch full detail for one grant: title, agency, description, response date.

    Use this to ground a tailored application draft in the opportunity's own text.
    """
    return to_grant_detail(_grants.fetch(opportunity_id))


def _pipe(codes: list[str] | None) -> str:
    return "|".join(codes) if codes else ""


def _bounded_limit(limit: int) -> int:
    try:
        value = int(limit)
    except (TypeError, ValueError):
        return _DEFAULT_SEARCH_LIMIT
    return max(1, min(value, _MAX_SEARCH_LIMIT))


if __name__ == "__main__":
    mcp.run()
