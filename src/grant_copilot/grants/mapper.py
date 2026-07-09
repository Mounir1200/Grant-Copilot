"""Normalize raw grants.gov records into the domain `Grant` model."""

from __future__ import annotations

import html
import re
from datetime import date, datetime

from grant_copilot.domain.models import Grant

_DETAIL_URL = "https://www.grants.gov/search-results-detail/{id}"
_CLOSE_DATE_FORMAT = "%m/%d/%Y"
_HTML_TAG = re.compile(r"<[^>]+>")


def to_grant(record: dict) -> Grant:
    """Map one `oppHits` record to a Grant (HTML-unescaped, dates parsed)."""
    opportunity_id = str(record["id"])
    return Grant(
        id=opportunity_id,
        title=html.unescape(record.get("title", "")).strip(),
        agency=record.get("agencyCode") or record.get("agency", ""),
        close_date=_parse_close_date(record.get("closeDate")),
        url=_DETAIL_URL.format(id=opportunity_id),
    )


def _parse_close_date(value: str | None) -> date | None:
    if not value:
        return None
    return datetime.strptime(value, _CLOSE_DATE_FORMAT).date()


def to_grant_detail(data: dict) -> dict:
    """Extract the fields a draft needs from a raw fetchOpportunity record."""
    synopsis = data.get("synopsis") or {}
    return {
        "id": str(data.get("id", "")),
        "title": html.unescape(data.get("opportunityTitle", "")).strip(),
        "agency": data.get("owningAgencyCode") or synopsis.get("agencyName", ""),
        "description": _strip_html(synopsis.get("synopsisDesc", "")),
    }


def _strip_html(text: str) -> str:
    return html.unescape(_HTML_TAG.sub(" ", text or "")).strip()
