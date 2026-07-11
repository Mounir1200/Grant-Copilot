"""Domain models shared across the app — source-agnostic and immutable."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from enum import Enum

_MAX_ACTIONABLE_HORIZON_DAYS = 5 * 366


@dataclass(frozen=True, slots=True)
class Grant:
    """A funding opportunity, normalized from any data source."""

    id: str
    title: str
    agency: str
    close_date: date | None
    url: str
    status: str = ""
    open_date: date | None = None

    def is_actionable(self, as_of: date | None = None) -> bool:
        """Return whether the opportunity is posted, open, and not past due."""
        today = as_of or date.today()
        normalized_status = self.status.strip().lower()
        if normalized_status != "posted":
            return False
        if self.open_date and self.open_date > today:
            return False
        # Without an explicit deadline the Slack UI cannot distinguish a rolling
        # opportunity from a stale Search2 record, so it is not actionable here.
        return (
            self.close_date is not None
            and today <= self.close_date <= today + timedelta(days=_MAX_ACTIONABLE_HORIZON_DAYS)
        )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "agency": self.agency,
            "close_date": self.close_date.isoformat() if self.close_date else None,
            "url": self.url,
            "status": self.status,
            "open_date": self.open_date.isoformat() if self.open_date else None,
        }

    @classmethod
    def from_dict(cls, data: dict) -> Grant:
        close_date = data.get("close_date")
        open_date = data.get("open_date")
        return cls(
            id=data["id"],
            title=data["title"],
            agency=data["agency"],
            close_date=date.fromisoformat(close_date) if close_date else None,
            url=data["url"],
            status=str(data.get("status") or ""),
            open_date=date.fromisoformat(open_date) if open_date else None,
        )


class PipelineStatus(str, Enum):
    """Where a saved grant sits in the application workflow."""

    TO_APPLY = "to_apply"
    IN_PROGRESS = "in_progress"
    SUBMITTED = "submitted"


@dataclass(frozen=True, slots=True)
class PipelineItem:
    """A grant a user is tracking, with its workflow status."""

    grant: Grant
    status: PipelineStatus
    saved_at: datetime


@dataclass(frozen=True, slots=True)
class OrgProfile:
    """A nonprofit profile that drives search pre-screening and drafting."""

    mission: str
    applicant_type: str = ""  # grants.gov eligibility code ("" = any)
    focus_areas: tuple[str, ...] = ()  # grants.gov funding category codes
