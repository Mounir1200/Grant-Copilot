"""Deadline reminders — a background job that DMs users about closing grants."""

from __future__ import annotations

import logging
from datetime import datetime

from apscheduler.schedulers.background import BackgroundScheduler
from slack_sdk import WebClient

from grant_copilot.domain.models import PipelineItem
from grant_copilot.domain.repositories import PipelineRepository
from grant_copilot.slack.format import date_label, mrkdwn_link

_logger = logging.getLogger(__name__)

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
    """Send each due reminder in isolation so one failure can't silence the rest."""
    for user_id, item in pipeline.due_soon(_WINDOW_DAYS):
        try:
            client.chat_postMessage(channel=user_id, text=_reminder_text(item))
            pipeline.mark_reminded(user_id, item.grant.id)
        except Exception:
            _logger.exception("Failed to send deadline reminder to %s", user_id)


def _reminder_text(item: PipelineItem) -> str:
    grant = item.grant
    return (
        f"*Deadline reminder* — {mrkdwn_link(grant.url, grant.title)} "
        f"closes {date_label(grant.close_date)}."
    )
