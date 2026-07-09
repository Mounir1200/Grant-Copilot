"""HTTP access to the grants.gov public Search2 API (no auth required).

Returns raw response records; turning them into domain models is the mapper's
job (single responsibility).
"""

from __future__ import annotations

import httpx

_BASE_URL = "https://api.grants.gov/v1/api"
_TIMEOUT_SECONDS = 15


class GrantsGovClient:
    """Thin wrapper over the grants.gov REST API."""

    def __init__(self, http: httpx.Client | None = None) -> None:
        self._http = http or httpx.Client(base_url=_BASE_URL, timeout=_TIMEOUT_SECONDS)

    def search(
        self,
        keyword: str,
        rows: int = 10,
        eligibilities: str = "",
        funding_categories: str = "",
        statuses: str = "posted|forecasted",
    ) -> list[dict]:
        """Return raw `oppHits` for a keyword and optional grants.gov facets."""
        body: dict = {"keyword": keyword, "rows": rows}
        if eligibilities:
            body["eligibilities"] = eligibilities
        if funding_categories:
            body["fundingCategories"] = funding_categories
        if statuses:
            body["oppStatuses"] = statuses
        response = self._http.post("/search2", json=body)
        response.raise_for_status()
        return response.json()["data"]["oppHits"]

    def fetch(self, opportunity_id: str) -> dict:
        """Return the raw detail record for a single opportunity."""
        response = self._http.post(
            "/fetchOpportunity", json={"opportunityId": int(opportunity_id)}
        )
        response.raise_for_status()
        return response.json()["data"]
