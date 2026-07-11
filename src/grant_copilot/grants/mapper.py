"""Normalize raw grants.gov records into the domain `Grant` model."""

from __future__ import annotations

import html
import re
from datetime import date, datetime

from grant_copilot.domain.models import Grant

_DETAIL_URL = "https://www.grants.gov/search-results-detail/{id}"
_CLOSE_DATE_FORMAT = "%m/%d/%Y"
_HTML_TAG = re.compile(r"<[^>]+>")
_ISO_DATE_PREFIX = re.compile(r"^\d{4}-\d{2}-\d{2}")
_MONTH_DATE_PREFIX = re.compile(r"^[A-Za-z]{3} \d{1,2}, \d{4}")


def to_grant(record: dict) -> Grant:
    """Map one `oppHits` record to a Grant (HTML-unescaped, dates parsed)."""
    opportunity_id = str(record["id"])
    return Grant(
        id=opportunity_id,
        title=html.unescape(record.get("title", "")).strip(),
        agency=record.get("agencyCode") or record.get("agency", ""),
        close_date=_parse_close_date(record.get("closeDate")),
        url=_DETAIL_URL.format(id=opportunity_id),
        status=str(record.get("oppStatus") or "").strip().lower(),
        open_date=_parse_close_date(record.get("openDate")),
    )


def _parse_close_date(value: object) -> date | None:
    """Parse the date forms emitted by search2 and fetchOpportunity."""
    if not value:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    text = str(value).strip()
    candidates: list[tuple[str, str]] = [(text, _CLOSE_DATE_FORMAT)]
    if match := _ISO_DATE_PREFIX.match(text):
        candidates.append((match.group(), "%Y-%m-%d"))
    if match := _MONTH_DATE_PREFIX.match(text):
        candidates.append((match.group(), "%b %d, %Y"))
    for candidate, date_format in candidates:
        try:
            return datetime.strptime(candidate, date_format).date()
        except ValueError:
            continue
    return None


def to_grant_detail(data: dict) -> dict:
    """Extract factual fields used to ground drafting and relevance ranking."""
    synopsis = data.get("synopsis") if isinstance(data.get("synopsis"), dict) else {}
    forecast = data.get("forecast") if isinstance(data.get("forecast"), dict) else {}
    source = synopsis or forecast
    status = str(
        data.get("ost")
        or data.get("oppStatus")
        or data.get("opportunityStatus")
        or data.get("status")
        or ""
    ).strip().lower()
    open_date = _first_date(
        data.get("openDate"),
        source.get("postingDateStr"),
        source.get("postingDate"),
        source.get("forecastPostingDateStr"),
        source.get("forecastPostingDate"),
    )
    close_date = _first_date(
        data.get("closeDate"),
        source.get("responseDateStr"),
        source.get("responseDate"),
        source.get("estimatedResponseDateStr"),
        source.get("estimatedResponseDate"),
    )
    return {
        "id": str(data.get("id", "")),
        "title": html.unescape(str(data.get("opportunityTitle") or "")).strip(),
        "agency": data.get("owningAgencyCode") or source.get("agencyName", ""),
        "description": _strip_html(
            source.get("synopsisDesc") or source.get("forecastDesc") or ""
        ),
        "eligibility": _descriptions(source.get("applicantTypes")),
        "eligibility_notes": _strip_html(
            source.get("applicantEligibilityDesc")
            or source.get("additionalInformationOnEligibility")
            or ""
        ),
        "funding_categories": _descriptions(source.get("fundingActivityCategories")),
        "status": status,
        "open_date": open_date.isoformat() if open_date else None,
        "close_date": close_date.isoformat() if close_date else None,
        "deadline_notes": _strip_html(source.get("responseDateDesc") or ""),
    }


def _first_date(*values: object) -> date | None:
    for value in values:
        if parsed := _parse_close_date(value):
            return parsed
    return None


def _descriptions(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    descriptions: list[str] = []
    for item in value:
        if isinstance(item, dict):
            label = item.get("description") or item.get("name") or item.get("id")
        else:
            label = item
        text = _strip_html(label)
        if text:
            descriptions.append(text)
    return descriptions


def _strip_html(text: object) -> str:
    return html.unescape(_HTML_TAG.sub(" ", str(text or ""))).strip()
