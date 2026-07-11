"""Curation result building — the pure pass that ranks and annotates grants."""

from __future__ import annotations

import asyncio
import json
from datetime import date, timedelta
from types import SimpleNamespace

import pytest

from grant_copilot.agent.orchestrator import (
    GrantAgent,
    _build_result,
    _catalog_entry,
    _match_summary,
    _quote_excerpt,
    _to_mistral_tools,
    _truncate_text,
    _validated_result,
)


def _iso(days: int) -> str:
    return (date.today() + timedelta(days=days)).isoformat()

_GRANTS = [
    {
        "id": "1",
        "title": "Rural education programs",
        "agency": "A1",
        "url": "https://example.test/1",
        "status": "posted",
        "open_date": _iso(-10),
        "close_date": _iso(30),
        "description": "Supports rural schools with after-school learning.",
        "eligibility": ["Nonprofit organizations"],
        "funding_categories": ["Education"],
    },
    {
        "id": "2",
        "title": "Community health access",
        "agency": "A2",
        "url": "https://example.test/2",
        "status": "posted",
        "open_date": _iso(-5),
        "close_date": _iso(45),
        "description": "Expands mobile health services in underserved areas.",
        "eligibility": ["Community nonprofits"],
        "funding_categories": ["Health"],
    },
]


def test_build_result_orders_and_annotates_by_picks() -> None:
    content = json.dumps(
        {
            "summary": "Two matches.",
            "picks": [
                {
                    "id": "2",
                    "reason": "Expands health access",
                    "evidence": "mobile health services",
                },
                {
                    "id": "1",
                    "reason": "Supports rural education",
                    "evidence": "Supports rural schools",
                },
            ],
        }
    )
    result = _build_result(content, _GRANTS)
    assert result.message == "Found 2 currently open, source-cited potential matches."
    assert [g["id"] for g in result.grants] == ["2", "1"]
    assert result.grants[0]["reason"] == "Expands health access"


def test_build_result_drops_picks_with_unknown_ids() -> None:
    content = json.dumps(
        {
            "summary": "s",
            "picks": [{"id": "999", "reason": "ghost", "evidence": "ghost"}],
        }
    )
    result = _build_result(content, _GRANTS)
    assert result.grants == []


def test_build_result_survives_malformed_json() -> None:
    result = _build_result("not json", _GRANTS)
    assert result.message == ""
    assert result.grants == []


def test_build_result_survives_valid_non_object_json() -> None:
    assert _build_result("null", _GRANTS).grants == []
    assert _build_result("[]", _GRANTS).grants == []


def test_validated_result_distinguishes_invalid_curation_from_no_match() -> None:
    with pytest.raises(RuntimeError, match="invalid structured data"):
        _validated_result("not json", _GRANTS)
    with pytest.raises(RuntimeError, match="no verifiable evidence"):
        _validated_result(
            json.dumps(
                {
                    "picks": [
                        {
                            "id": "1",
                            "reason": "Unsupported",
                            "evidence": "not present in the synopsis",
                        }
                    ]
                }
            ),
            _GRANTS,
        )
    assert _validated_result(json.dumps({"picks": []}), _GRANTS).grants == []


def test_build_result_keeps_an_explicit_empty_shortlist_empty() -> None:
    result = _build_result(
        json.dumps({"summary": "No evidence-backed matches.", "picks": []}),
        _GRANTS,
    )
    assert result.message == ""
    assert result.grants == []


def test_build_result_requires_grounded_evidence() -> None:
    content = json.dumps(
        {
            "summary": "One grounded match.",
            "picks": [
                {
                    "id": "2",
                    "reason": "Invented claim",
                    "evidence": "guaranteed awards",
                },
                {
                    "id": "1",
                    "reason": "Supports rural education",
                    "evidence": "Supports rural schools",
                },
            ],
        }
    )

    result = _build_result(content, _GRANTS)

    assert [grant["id"] for grant in result.grants] == ["1"]


def test_title_or_broad_category_alone_is_not_fit_evidence() -> None:
    content = json.dumps(
        {
            "summary": "Unsupported match.",
            "picks": [
                {
                    "id": "1",
                    "reason": "Claims a fit from the title alone",
                    "evidence": "Rural education programs",
                },
                {
                    "id": "2",
                    "reason": "Claims a fit from a category alone",
                    "evidence": "Community nonprofits",
                },
            ],
        }
    )
    assert _build_result(content, _GRANTS).grants == []


def test_build_result_never_resurrects_an_expired_grant() -> None:
    expired = {**_GRANTS[0], "close_date": _iso(-1)}
    content = json.dumps(
        {
            "summary": "A match.",
            "picks": [
                {
                    "id": "1",
                    "reason": "Supports rural education",
                    "evidence": "Supports rural schools",
                }
            ],
        }
    )

    assert _build_result(content, [expired]).grants == []


def test_only_search_tool_is_exposed_to_mistral() -> None:
    listing = SimpleNamespace(
        tools=[
            SimpleNamespace(name="search_grants", description="search", inputSchema={}),
            SimpleNamespace(name="get_grant", description="detail", inputSchema={}),
        ]
    )

    tools = _to_mistral_tools(listing)

    assert [tool["function"]["name"] for tool in tools] == ["search_grants"]
    assert tools[0]["function"]["parameters"]["additionalProperties"] is False


def test_search_model_without_a_tool_call_is_a_technical_error() -> None:
    class FakeMistral:
        def __init__(self) -> None:
            self.chat = SimpleNamespace(complete=self.complete)

        def complete(self, **kwargs):
            message = SimpleNamespace(content="", tool_calls=None)
            return SimpleNamespace(choices=[SimpleNamespace(message=message)])

    agent = GrantAgent(FakeMistral())
    with pytest.raises(RuntimeError, match="did not call search_grants"):
        asyncio.run(agent._search(SimpleNamespace(), [{}], "water", None))


def test_catalog_contains_bounded_factual_evidence() -> None:
    grant = {**_GRANTS[0], "description": "x" * 3000}

    entry = _catalog_entry(grant)

    assert len(entry["synopsis"]) == 1600
    assert entry["eligibility"] == ["Nonprofit organizations"]
    assert entry["funding_categories"] == ["Education"]
    assert entry["status"] == "posted"
    assert entry["open_date"] == grant["open_date"]
    assert entry["close_date"] == grant["close_date"]


def test_long_reason_is_truncated_at_a_word_boundary() -> None:
    text = _truncate_text("one two three four five", 15)
    assert text == "one two three…"
    assert len(text) <= 15


def test_match_summary_uses_only_the_validated_count() -> None:
    assert _match_summary(0) == ""
    assert _match_summary(1) == "Found 1 currently open, source-cited potential match."
    assert _match_summary(3) == "Found 3 currently open, source-cited potential matches."


def test_long_evidence_keeps_an_exact_prefix_without_ellipsis() -> None:
    source = "one two three four five"
    excerpt = _quote_excerpt(source, 15)
    assert excerpt == "one two three"
    assert source.startswith(excerpt)


def test_shortlist_is_enriched_with_get_grant_before_curation() -> None:
    class FakeSession:
        def __init__(self) -> None:
            self.calls: list[tuple[str, dict]] = []

        async def call_tool(self, name: str, arguments: dict):
            self.calls.append((name, arguments))
            payload = {
                "id": arguments["opportunity_id"],
                "title": "Detailed title",
                "agency": "A1",
                "description": "Supports rural schools with tutoring.",
                "eligibility": ["Nonprofit organizations"],
                "funding_categories": ["Education"],
                "status": "posted",
                "open_date": _iso(-10),
                "close_date": _iso(30),
            }
            return SimpleNamespace(
                isError=False,
                content=[SimpleNamespace(type="text", text=json.dumps(payload))],
            )

    session = FakeSession()
    agent = GrantAgent(None)  # type: ignore[arg-type]

    enriched = asyncio.run(agent._enrich_grants(session, [_GRANTS[0]]))

    assert session.calls == [("get_grant", {"opportunity_id": "1"})]
    assert enriched[0]["description"] == "Supports rural schools with tutoring."
    assert enriched[0]["detail_available"] is True


def test_total_detail_outage_is_not_reported_as_no_match() -> None:
    class FailingSession:
        async def call_tool(self, name: str, arguments: dict):
            raise TimeoutError("upstream unavailable")

    agent = GrantAgent(None)  # type: ignore[arg-type]
    with pytest.raises(RuntimeError, match="temporarily unavailable"):
        asyncio.run(agent._enrich_grants(FailingSession(), [_GRANTS[0]]))
