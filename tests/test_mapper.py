"""Normalizing raw grants.gov records into domain models."""

from __future__ import annotations

from datetime import date

from grant_copilot.grants.mapper import (
    _DETAIL_URL,
    _parse_close_date,
    _strip_html,
    to_grant,
    to_grant_detail,
)


def test_to_grant_unescapes_and_parses() -> None:
    grant = to_grant(
        {
            "id": 123,
            "title": "Youth STEM &amp; Arts",
            "agencyCode": "ED",
            "closeDate": "03/02/2027",
        }
    )
    assert grant.id == "123"
    assert grant.title == "Youth STEM & Arts"
    assert grant.agency == "ED"
    assert grant.close_date == date(2027, 3, 2)
    assert grant.url == _DETAIL_URL.format(id="123")


def test_to_grant_falls_back_to_agency_and_missing_close_date() -> None:
    grant = to_grant({"id": 9, "title": "T", "agency": "Dept of X"})
    assert grant.agency == "Dept of X"
    assert grant.close_date is None


def test_parse_close_date_handles_empty() -> None:
    assert _parse_close_date(None) is None
    assert _parse_close_date("03/02/2027") == date(2027, 3, 2)


def test_to_grant_detail_extracts_only_draftable_fields() -> None:
    detail = to_grant_detail(
        {
            "id": 42,
            "opportunityTitle": "Clean Water &amp; Land",
            "synopsis": {
                "agencyName": "EPA",
                "synopsisDesc": "<p>Fund rivers.</p>",
            },
        }
    )
    assert detail == {
        "id": "42",
        "title": "Clean Water & Land",
        "agency": "EPA",
        "description": "Fund rivers.",
    }
    # The now-removed field must not creep back into the payload.
    assert "response_date" not in detail


def test_strip_html_unescapes_and_removes_tags() -> None:
    assert _strip_html("<p>Hello &amp; bye</p>") == "Hello & bye"
