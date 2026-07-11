"""App Home safety, trust copy, ordering, and Slack block limits."""

from __future__ import annotations

from datetime import date, datetime, timedelta

from grant_copilot.domain.models import Grant, OrgProfile, PipelineItem, PipelineStatus
from grant_copilot.slack.home import draft_modal, home_view


def _item(index: int, status: PipelineStatus, days: int | None = None) -> PipelineItem:
    close_date = date.today() + timedelta(days=days) if days is not None else None
    return PipelineItem(
        grant=Grant(
            id=str(index),
            title=f"Grant {index}",
            agency="EPA",
            close_date=close_date,
            url=f"https://www.grants.gov/search-results-detail/{index}",
        ),
        status=status,
        saved_at=datetime(2026, 7, 1, 12, 0, index % 60),
    )


def test_home_is_bounded_below_slacks_100_block_limit() -> None:
    items = [
        _item(index, status, index + 1)
        for status in PipelineStatus
        for index in range(12)
    ]
    view = home_view(items, OrgProfile(mission="Rural youth STEM"))
    assert len(view["blocks"]) < 100
    assert any("Showing the 8 nearest deadlines" in str(block) for block in view["blocks"])


def test_home_orders_each_stage_by_nearest_deadline() -> None:
    view = home_view(
        [
            _item(20, PipelineStatus.TO_APPLY, 20),
            _item(5, PipelineStatus.TO_APPLY, 5),
            _item(99, PipelineStatus.TO_APPLY, None),
        ],
        None,
    )
    rendered = "\n".join(str(block) for block in view["blocks"])
    assert rendered.index("Grant 5") < rendered.index("Grant 20") < rendered.index("Grant 99")


def test_home_discloses_source_ai_processing_and_data_deletion() -> None:
    view = home_view([], None)
    rendered = "\n".join(str(block) for block in view["blocks"])
    assert "This product uses the Grants.gov API" in rendered
    assert "Search and draft context is sent to Mistral AI" in rendered
    assert "delete_user_data" in rendered


def test_draft_modal_promotes_each_needs_input_marker() -> None:
    summary = (
        "The organization will refine its project plan. "
        "[NEEDS INPUT: target population and geographic scope.] "
        "The final plan should be reviewed. "
        "[NEEDS INPUT: measurable outcomes.]"
    )

    view = draft_modal("Community Health", summary)

    assert len(view["blocks"]) == 4
    rendered_summary = view["blocks"][2]["text"]["text"]
    assert "\n\n:warning: *[NEEDS INPUT: target population and geographic scope.]*" in (
        rendered_summary
    )
    assert "\n\n:warning: *[NEEDS INPUT: measurable outcomes.]*" in rendered_summary


def test_draft_modal_escapes_markers_and_keeps_plain_drafts_compact() -> None:
    marked = draft_modal("Title", "[NEEDS INPUT: <verified> & approved information]")
    assert "&lt;verified&gt; &amp; approved information" in marked["blocks"][2]["text"]["text"]

    unmarked = draft_modal("Title", "A cautious draft with no missing data markers.")
    assert len(unmarked["blocks"]) == 4
