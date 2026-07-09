"""SQLite implementations of the domain repositories."""

from __future__ import annotations

from datetime import date, datetime

from grant_copilot.domain.models import (
    Grant,
    OrgProfile,
    PipelineItem,
    PipelineStatus,
)
from grant_copilot.infra.db import session


class SqlitePipelineRepository:
    def __init__(self, path: str) -> None:
        self._path = path

    def save(self, user_id: str, grant: Grant) -> None:
        with session(self._path) as connection:
            connection.execute(
                """INSERT OR IGNORE INTO pipeline
                   (user_id, grant_id, title, agency, close_date, url, status, saved_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    user_id,
                    grant.id,
                    grant.title,
                    grant.agency,
                    grant.close_date.isoformat() if grant.close_date else None,
                    grant.url,
                    PipelineStatus.TO_APPLY.value,
                    datetime.now().isoformat(timespec="seconds"),
                ),
            )

    def list(self, user_id: str) -> list[PipelineItem]:
        with session(self._path) as connection:
            rows = connection.execute(
                "SELECT * FROM pipeline WHERE user_id = ? ORDER BY saved_at DESC",
                (user_id,),
            ).fetchall()
        return [_row_to_item(row) for row in rows]

    def set_status(self, user_id: str, grant_id: str, status: PipelineStatus) -> None:
        with session(self._path) as connection:
            connection.execute(
                "UPDATE pipeline SET status = ? WHERE user_id = ? AND grant_id = ?",
                (status.value, user_id, grant_id),
            )

    def remove(self, user_id: str, grant_id: str) -> None:
        with session(self._path) as connection:
            connection.execute(
                "DELETE FROM pipeline WHERE user_id = ? AND grant_id = ?",
                (user_id, grant_id),
            )

    def due_soon(self, within_days: int) -> list[tuple[str, PipelineItem]]:
        with session(self._path) as connection:
            rows = connection.execute(
                """SELECT * FROM pipeline
                   WHERE close_date IS NOT NULL AND reminded = 0 AND status != ?
                     AND close_date BETWEEN date('now') AND date('now', ?)
                   ORDER BY close_date""",
                (PipelineStatus.SUBMITTED.value, f"+{within_days} days"),
            ).fetchall()
        return [(row["user_id"], _row_to_item(row)) for row in rows]

    def mark_reminded(self, user_id: str, grant_id: str) -> None:
        with session(self._path) as connection:
            connection.execute(
                "UPDATE pipeline SET reminded = 1 WHERE user_id = ? AND grant_id = ?",
                (user_id, grant_id),
            )


class SqliteProfileRepository:
    def __init__(self, path: str) -> None:
        self._path = path

    def get(self, user_id: str) -> OrgProfile | None:
        with session(self._path) as connection:
            row = connection.execute(
                "SELECT summary, applicant_type, focus_areas FROM mission WHERE user_id = ?",
                (user_id,),
            ).fetchone()
        if row is None:
            return None
        return OrgProfile(
            mission=row["summary"],
            applicant_type=row["applicant_type"] or "",
            focus_areas=tuple(
                code for code in (row["focus_areas"] or "").split(",") if code
            ),
        )

    def save(self, user_id: str, profile: OrgProfile) -> None:
        with session(self._path) as connection:
            connection.execute(
                """INSERT INTO mission (user_id, summary, applicant_type, focus_areas)
                   VALUES (?, ?, ?, ?)
                   ON CONFLICT(user_id) DO UPDATE SET
                       summary = excluded.summary,
                       applicant_type = excluded.applicant_type,
                       focus_areas = excluded.focus_areas""",
                (
                    user_id,
                    profile.mission,
                    profile.applicant_type,
                    ",".join(profile.focus_areas),
                ),
            )


def _row_to_item(row) -> PipelineItem:
    close_date = row["close_date"]
    grant = Grant(
        id=row["grant_id"],
        title=row["title"],
        agency=row["agency"],
        close_date=date.fromisoformat(close_date) if close_date else None,
        url=row["url"],
    )
    return PipelineItem(
        grant=grant,
        status=PipelineStatus(row["status"]),
        saved_at=datetime.fromisoformat(row["saved_at"]),
    )
