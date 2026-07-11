"""Regression tests for actionability filtering at the MCP boundary."""

from __future__ import annotations

from datetime import date, timedelta

from grant_copilot import mcp_server
from grant_copilot.domain.models import Grant


def _api_date(value: date) -> str:
    return value.strftime("%m/%d/%Y")


def _record(
    grant_id: str,
    *,
    status: str = "posted",
    open_date: date | str | None,
    close_date: date | str | None,
) -> dict:
    return {
        "id": grant_id,
        "title": f"Grant {grant_id}",
        "agencyCode": "EPA",
        "oppStatus": status,
        "openDate": _api_date(open_date) if isinstance(open_date, date) else open_date or "",
        "closeDate": (
            _api_date(close_date) if isinstance(close_date, date) else close_date or ""
        ),
    }


def test_old_posted_record_without_deadline_is_not_actionable() -> None:
    stale = Grant(
        id="climate-fy2012",
        title="Climate FY2012",
        agency="EPA",
        close_date=None,
        url="https://example.test/stale",
        status="posted",
        open_date=date(2011, 9, 1),
    )

    assert not stale.is_actionable(as_of=date(2026, 7, 11))


def test_far_future_sentinel_deadline_is_not_actionable() -> None:
    sentinel = Grant(
        id="fy2022-placeholder",
        title="Program FY2022",
        agency="DOS",
        close_date=date(2099, 1, 1),
        url="https://example.test/sentinel",
        status="posted",
        open_date=date(2022, 1, 21),
    )

    assert not sentinel.is_actionable(as_of=date(2026, 7, 11))


def test_mcp_returns_only_current_posted_opportunities(monkeypatch) -> None:
    today = date.today()

    class FakeClient:
        def __init__(self) -> None:
            self.rows = 0

        def search(self, keyword: str, **kwargs) -> list[dict]:
            self.rows = kwargs["rows"]
            return [
                _record(
                    "active",
                    open_date=today - timedelta(days=10),
                    close_date=today + timedelta(days=30),
                ),
                _record(
                    "climate-fy2012",
                    open_date=date(2011, 9, 1),
                    close_date="",
                ),
                _record(
                    "expired",
                    open_date=today - timedelta(days=60),
                    close_date=today - timedelta(days=1),
                ),
                _record(
                    "forecast",
                    status="forecasted",
                    open_date=today + timedelta(days=10),
                    close_date=today + timedelta(days=60),
                ),
                _record(
                    "fy2022-placeholder",
                    open_date=date(2022, 1, 21),
                    close_date=date(2099, 1, 1),
                ),
            ]

    fake = FakeClient()
    monkeypatch.setattr(mcp_server, "_grants", fake)

    result = mcp_server.search_grants("climate", limit=10)

    assert [grant["id"] for grant in result["grants"]] == ["active"]
    assert result["grants"][0]["status"] == "posted"
    assert fake.rows == 20  # search deeper so stale records do not empty the shortlist
