"""Deadline reminders — a background job that DMs users about closing grants."""

from __future__ import annotations

from datetime import datetime

from apscheduler.schedulers.background import BackgroundScheduler
from slack_sdk import WebClient

from grant_copilot.domain.models import PipelineItem
from grant_copilot.domain.repositories import PipelineRepository
from grant_copilot.slack.format import mrkdwn_link

_WINDOW_DAYS = 30
_INTERVAL_HOURS = 24


def start_reminders(
    client: WebClient, pipeline: PipelineRepository
) -> BackgroundScheduler:
    """Run the reminder check now and once a day; return the running scheduler."""
    scheduler = BackgroundScheduler()
    scheduler.add_job(
        lambda: _send_due_reminders(client, pipeline),
        trigger="interval",
        hours=_INTERVAL_HOURS,
        next_run_time=datetime.now(),
    )
    scheduler.start()
    return scheduler


def _send_due_reminders(client: WebClient, pipeline: PipelineRepository) -> None:
    for user_id, item in pipeline.due_soon(_WINDOW_DAYS):
        client.chat_postMessage(channel=user_id, text=_reminder_text(item))
        pipeline.mark_reminded(user_id, item.grant.id)


def _reminder_text(item: PipelineItem) -> str:
    grant = item.grant
    when = f"{grant.close_date.strftime('%b')} {grant.close_date.day}, {grant.close_date.year}"
    return f"*Deadline reminder* — {mrkdwn_link(grant.url, grant.title)} closes {when}."
