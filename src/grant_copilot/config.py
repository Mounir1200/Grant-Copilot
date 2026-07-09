"""Application configuration loaded from the environment."""

from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

_DEFAULT_DB_PATH = "grant_copilot.db"


@dataclass(frozen=True, slots=True)
class Settings:
    """Runtime settings required to start the Slack app and its agent."""

    slack_bot_token: str
    slack_app_token: str
    mistral_api_key: str
    db_path: str = _DEFAULT_DB_PATH

    @classmethod
    def load(cls) -> Settings:
        load_dotenv()
        return cls(
            slack_bot_token=_require("SLACK_BOT_TOKEN"),
            slack_app_token=_require("SLACK_APP_TOKEN"),
            mistral_api_key=_require("MISTRAL_API_KEY"),
            db_path=os.environ.get("GRANT_COPILOT_DB", _DEFAULT_DB_PATH),
        )


def _require(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value
