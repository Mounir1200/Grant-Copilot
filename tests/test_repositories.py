"""SQLite repositories — persistence, per-user isolation, reminder windowing."""

from __future__ import annotations

from datetime import date, timedelta

import pytest

from grant_copilot.domain.models import Grant, OrgProfile, PipelineStatus
from grant_copilot.infra.db import init
from grant_copilot.infra.repositories import (
    SqlitePipelineRepository,
    SqliteProfileRepository,
)

_USER = "U1"
_OTHER = "U2"


@pytest.fixture
def db_path(tmp_path) -> str:
    path = str(tmp_path / "test.db")
    init(path)
    return path


def _grant(grant_id: str = "1", close_date: date | None = None) -> Grant:
    return Grant(
        id=grant_id,
        title=f"Grant {grant_id}",
        agency="EPA",
        close_date=close_date,
        url=f"https://g/{grant_id}",
    )


def test_save_and_list_defaults_to_to_apply(db_path: str) -> None:
    repo = SqlitePipelineRepository(db_path)
    repo.save(_USER, _grant())
    items = repo.list(_USER)
    assert len(items) == 1
    assert items[0].grant == _grant()
    assert items[0].status is PipelineStatus.TO_APPLY


def test_pipeline_is_isolated_per_user(db_path: str) -> None:
    repo = SqlitePipelineRepository(db_path)
    repo.save(_USER, _grant())
    assert repo.list(_OTHER) == []


def test_set_status_and_remove(db_path: str) -> None:
    repo = SqlitePipelineRepository(db_path)
    repo.save(_USER, _grant())
    repo.set_status(_USER, "1", PipelineStatus.IN_PROGRESS)
    assert repo.list(_USER)[0].status is PipelineStatus.IN_PROGRESS
    repo.remove(_USER, "1")
    assert repo.list(_USER) == []


def test_due_soon_windows_and_marking(db_path: str) -> None:
    repo = SqlitePipelineRepository(db_path)
    near = date.today() + timedelta(days=10)
    far = date.today() + timedelta(days=100)
    repo.save(_USER, _grant("near", near))
    repo.save(_USER, _grant("far", far))

    due = repo.due_soon(within_days=30)
    assert [item.grant.id for _, item in due] == ["near"]

    repo.mark_reminded(_USER, "near")
    assert repo.due_soon(within_days=30) == []


def test_due_soon_ignores_submitted(db_path: str) -> None:
    repo = SqlitePipelineRepository(db_path)
    near = date.today() + timedelta(days=5)
    repo.save(_USER, _grant("near", near))
    repo.set_status(_USER, "near", PipelineStatus.SUBMITTED)
    assert repo.due_soon(within_days=30) == []


def test_profile_get_returns_none_before_save(db_path: str) -> None:
    assert SqliteProfileRepository(db_path).get(_USER) is None


def test_profile_round_trips_and_upserts(db_path: str) -> None:
    repo = SqliteProfileRepository(db_path)
    profile = OrgProfile(
        mission="Clean water access",
        applicant_type="12",
        focus_areas=("ED", "HL"),
    )
    repo.save(_USER, profile)
    assert repo.get(_USER) == profile

    updated = OrgProfile(mission="New mission", applicant_type="", focus_areas=())
    repo.save(_USER, updated)
    assert repo.get(_USER) == updated
