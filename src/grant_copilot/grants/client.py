"""HTTP access to the grants.gov public Search2 API (no auth required).

Returns raw response records; turning them into domain models is the mapper's
job (single responsibility).
"""

from __future__ import annotations

import time
from collections.abc import Callable

import httpx

_BASE_URL = "https://api.grants.gov/v1/api"
_TIMEOUT_SECONDS = 10
_DEFAULT_MAX_ATTEMPTS = 2
_DEFAULT_BACKOFF_SECONDS = 0.25
_MAX_RETRY_DELAY_SECONDS = 2.0
_RETRYABLE_STATUS_CODES = frozenset({429, 500, 502, 503, 504})


class GrantsGovClient:
    """Thin wrapper over the grants.gov REST API."""

    def __init__(
        self,
        http: httpx.Client | None = None,
        *,
        max_attempts: int = _DEFAULT_MAX_ATTEMPTS,
        backoff_seconds: float = _DEFAULT_BACKOFF_SECONDS,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self._http = http or httpx.Client(base_url=_BASE_URL, timeout=_TIMEOUT_SECONDS)
        self._max_attempts = max(1, int(max_attempts))
        self._backoff_seconds = max(0.0, float(backoff_seconds))
        self._sleep = sleep

    def search(
        self,
        keyword: str,
        rows: int = 10,
        eligibilities: str = "",
        funding_categories: str = "",
        statuses: str = "posted",
    ) -> list[dict]:
        """Return raw `oppHits` for a keyword and optional grants.gov facets."""
        body: dict = {"keyword": keyword, "rows": rows}
        if eligibilities:
            body["eligibilities"] = eligibilities
        if funding_categories:
            body["fundingCategories"] = funding_categories
        if statuses:
            body["oppStatuses"] = statuses
        data = self._response_data(self._post("/search2", body))
        hits = data.get("oppHits")
        if not isinstance(hits, list):
            raise ValueError("grants.gov search response is missing data.oppHits")
        return [record for record in hits if isinstance(record, dict)]

    def fetch(self, opportunity_id: str) -> dict:
        """Return the raw detail record for a single opportunity."""
        return self._response_data(
            self._post(
                "/fetchOpportunity",
                {"opportunityId": int(opportunity_id)},
                max_attempts=1,
            )
        )

    def _post(
        self, path: str, body: dict, *, max_attempts: int | None = None
    ) -> httpx.Response:
        attempts = self._max_attempts if max_attempts is None else max(1, max_attempts)
        for attempt in range(attempts):
            try:
                response = self._http.post(path, json=body)
            except httpx.TransportError:
                if attempt + 1 >= attempts:
                    raise
                self._sleep(self._retry_delay(attempt))
                continue

            if (
                response.status_code in _RETRYABLE_STATUS_CODES
                and attempt + 1 < attempts
            ):
                self._sleep(self._retry_delay(attempt, response))
                continue
            response.raise_for_status()
            return response
        raise RuntimeError("unreachable grants.gov retry state")

    def _retry_delay(self, attempt: int, response: httpx.Response | None = None) -> float:
        if response is not None:
            retry_after = response.headers.get("Retry-After", "")
            try:
                return min(max(0.0, float(retry_after)), _MAX_RETRY_DELAY_SECONDS)
            except ValueError:
                pass
        return min(self._backoff_seconds * (2**attempt), _MAX_RETRY_DELAY_SECONDS)

    @staticmethod
    def _response_data(response: httpx.Response) -> dict:
        try:
            payload = response.json()
        except ValueError as error:
            raise ValueError("grants.gov returned invalid JSON") from error
        if not isinstance(payload, dict):
            raise ValueError("grants.gov response must be a JSON object")
        error_code = payload.get("errorcode")
        if error_code not in (None, 0, "0"):
            message = str(payload.get("msg") or "unknown API error")
            raise ValueError(f"grants.gov error {error_code}: {message}")
        data = payload.get("data")
        if not isinstance(data, dict):
            raise ValueError("grants.gov response is missing data")
        return data
