"""Bolt application entry point (Socket Mode)."""

from __future__ import annotations

import logging

from mistralai.client import Mistral
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler

from grant_copilot.agent.drafter import Drafter
from grant_copilot.agent.orchestrator import GrantAgent
from grant_copilot.config import Settings
from grant_copilot.infra import db
from grant_copilot.infra.repositories import (
    SqlitePipelineRepository,
    SqliteProfileRepository,
)
from grant_copilot.infra.scheduler import start_reminders
from grant_copilot.slack import actions, assistant


def build_app(settings: Settings) -> App:
    """Create the Bolt app, wire the agent, storage, and reminders, and register surfaces."""
    db.init(settings.db_path)
    pipeline = SqlitePipelineRepository(settings.db_path)
    profile = SqliteProfileRepository(settings.db_path)
    mistral = Mistral(api_key=settings.mistral_api_key)

    app = App(token=settings.slack_bot_token)
    assistant.register(app, GrantAgent(mistral), profile)
    actions.register(app, pipeline, profile, Drafter(mistral))
    start_reminders(app.client, pipeline)
    return app


def run() -> None:
    logging.basicConfig(level=logging.INFO)
    settings = Settings.load()
    app = build_app(settings)
    SocketModeHandler(app, settings.slack_app_token).start()


if __name__ == "__main__":
    run()
