"""Profile-save handler — defense-in-depth validation of submitted codes."""

from __future__ import annotations

from grant_copilot.domain.models import OrgProfile
from grant_copilot.slack.actions import _save_profile_handler


class _FakeProfileRepo:
    def __init__(self) -> None:
        self.saved: OrgProfile | None = None

    def save(self, user_id: str, profile: OrgProfile) -> None:
        self.saved = profile

    def get(self, user_id: str) -> OrgProfile | None:
        return self.saved


class _FakePipelineRepo:
    def list(self, user_id: str) -> list:
        return []


class _FakeClient:
    def views_publish(self, **kwargs) -> None:
        pass


def _run(values: dict) -> OrgProfile:
    profile = _FakeProfileRepo()
    handler = _save_profile_handler(_FakePipelineRepo(), profile)
    handler(
        ack=lambda: None,
        body={"user": {"id": "U1"}},
        view={"state": {"values": values}},
        client=_FakeClient(),
    )
    assert profile.saved is not None
    return profile.saved


def test_valid_codes_are_kept() -> None:
    saved = _run(
        {
            "applicant": {"value": {"selected_option": {"value": "12"}}},
            "focus": {"value": {"selected_options": [{"value": "ED"}, {"value": "HL"}]}},
            "mission": {"value": {"value": "Clean water access"}},
        }
    )
    assert saved.applicant_type == "12"
    assert saved.focus_areas == ("ED", "HL")
    assert saved.mission == "Clean water access"


def test_unknown_codes_are_dropped() -> None:
    saved = _run(
        {
            "applicant": {"value": {"selected_option": {"value": "999"}}},
            "focus": {"value": {"selected_options": [{"value": "ED"}, {"value": "ZZ"}]}},
            "mission": {"value": {"value": "Water"}},
        }
    )
    assert saved.applicant_type == ""  # invalid applicant code falls back to "any"
    assert saved.focus_areas == ("ED",)  # bogus focus code filtered out
