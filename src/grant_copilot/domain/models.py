"""Domain models shared across the app — source-agnostic and immutable."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from enum import Enum


@dataclass(frozen=True, slots=True)
class Grant:
    """A funding opportunity, normalized from any data source."""

    id: str
    title: str
    agency: str
    close_date: date | None
    url: str

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "agency": self.agency,
            "close_date": self.close_date.isoformat() if self.close_date else None,
            "url": self.url,
        }

    @classmethod
    def from_dict(cls, data: dict) -> Grant:
        close_date = data.get("close_date")
        return cls(
            id=data["id"],
            title=data["title"],
            agency=data["agency"],
            close_date=date.fromisoformat(close_date) if close_date else None,
            url=data["url"],
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
    """A nonprofit's profile — drives eligibility-aware search and drafting."""

    mission: str
    applicant_type: str = ""  # grants.gov eligibility code ("" = any)
    focus_areas: tuple[str, ...] = ()  # grants.gov funding category codes
