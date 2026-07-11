"""HTTP boundary behavior for the grants.gov client."""

from __future__ import annotations

import json

import httpx
import pytest

from grant_copilot.grants.client import GrantsGovClient


def _client(handler, **kwargs) -> GrantsGovClient:
    http = httpx.Client(
        base_url="https://api.grants.gov/v1/api",
        transport=httpx.MockTransport(handler),
    )
    return GrantsGovClient(http, backoff_seconds=0, **kwargs)


def test_search_requests_posted_only_and_validates_hits() -> None:
    captured: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured.update(json.loads(request.content))
        return httpx.Response(
            200,
            json={"errorcode": 0, "data": {"oppHits": [{"id": "1"}, "bad"]}},
        )

    records = _client(handler).search(
        "water", eligibilities="12", funding_categories="ENV"
    )

    assert records == [{"id": "1"}]
    assert captured["oppStatuses"] == "posted"
    assert captured["eligibilities"] == "12"
    assert captured["fundingCategories"] == "ENV"


def test_transient_http_failure_is_retried_with_a_bound() -> None:
    attempts = 0
    sleeps: list[float] = []

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            return httpx.Response(503, headers={"Retry-After": "0"})
        return httpx.Response(200, json={"errorcode": 0, "data": {"oppHits": []}})

    client = _client(handler, max_attempts=2, sleep=sleeps.append)
    assert client.search("health") == []
    assert attempts == 2
    assert sleeps == [0.0]


def test_non_retryable_http_failure_is_not_retried() -> None:
    attempts = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        return httpx.Response(400)

    with pytest.raises(httpx.HTTPStatusError):
        _client(handler).search("health")
    assert attempts == 1


def test_fetch_detail_does_not_multiply_sequential_timeout_cost() -> None:
    attempts = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        return httpx.Response(503)

    with pytest.raises(httpx.HTTPStatusError):
        _client(handler, max_attempts=3).fetch("123")
    assert attempts == 1


def test_invalid_api_shape_is_rejected() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"errorcode": 0, "data": {}})

    with pytest.raises(ValueError, match="oppHits"):
        _client(handler).search("health")


def test_api_error_payload_is_rejected() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"errorcode": 12, "msg": "bad query"})

    with pytest.raises(ValueError, match="bad query"):
        _client(handler).search("health")
