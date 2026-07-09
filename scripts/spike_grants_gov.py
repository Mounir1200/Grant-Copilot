"""Smoke test for the grants.gov Search2 API (public, no auth required).

Confirms the response shape before the MCP server wraps it in Phase 1.

    uv run python scripts/spike_grants_gov.py "clean water"
"""

from __future__ import annotations

import sys

import httpx

SEARCH_URL = "https://api.grants.gov/v1/api/search2"


def search(keyword: str, rows: int = 5) -> list[dict]:
    response = httpx.post(
        SEARCH_URL, json={"keyword": keyword, "rows": rows}, timeout=15
    )
    response.raise_for_status()
    return response.json()["data"]["oppHits"]


def main() -> None:
    keyword = sys.argv[1] if len(sys.argv) > 1 else "education"
    hits = search(keyword)
    print(f"Top {len(hits)} grants for '{keyword}':\n")
    for hit in hits:
        print(
            f"- {hit.get('title')}  [{hit.get('agencyCode')}]  close: {hit.get('closeDate')}"
        )


if __name__ == "__main__":
    main()
