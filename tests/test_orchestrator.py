"""Curation result building — the pure pass that ranks and annotates grants."""

from __future__ import annotations

import json

from grant_copilot.agent.orchestrator import _build_result

_GRANTS = [
    {"id": "1", "title": "T1", "agency": "A1"},
    {"id": "2", "title": "T2", "agency": "A2"},
]


def test_build_result_orders_and_annotates_by_picks() -> None:
    content = json.dumps(
        {
            "summary": "Two matches.",
            "picks": [
                {"id": "2", "reason": "closest fit"},
                {"id": "1", "reason": "also relevant"},
            ],
        }
    )
    result = _build_result(content, _GRANTS)
    assert result.message == "Two matches."
    assert [g["id"] for g in result.grants] == ["2", "1"]
    assert result.grants[0]["reason"] == "closest fit"


def test_build_result_drops_picks_with_unknown_ids() -> None:
    content = json.dumps({"summary": "s", "picks": [{"id": "999", "reason": "ghost"}]})
    result = _build_result(content, _GRANTS)
    # No valid picks -> fall back to the raw grants so the user still sees results.
    assert result.grants == _GRANTS


def test_build_result_survives_malformed_json() -> None:
    result = _build_result("not json", _GRANTS)
    assert result.message == ""
    assert result.grants == _GRANTS
