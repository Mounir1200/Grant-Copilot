"""Block Kit rendering for grant results and the Save button payload."""

from __future__ import annotations

import json
from datetime import date

from grant_copilot.domain.models import Grant
from grant_copilot.slack.blocks import grant_results


def _button_values(blocks: list[dict]) -> list[dict]:
    return [
        json.loads(block["accessory"]["value"])
        for block in blocks
        if block.get("accessory")
    ]


def test_save_button_carries_only_domain_fields() -> None:
    grant = Grant("1", "T", "A", date(2027, 3, 2), "https://g/1").to_dict()
    grant["reason"] = "matches your mission"  # added by curation, not persisted
    payloads = _button_values(grant_results("Two matches.", [grant]))
    assert len(payloads) == 1
    assert set(payloads[0]) == {"id", "title", "agency", "close_date", "url"}


def test_empty_results_render_a_single_hint() -> None:
    assert len(grant_results("", [])) == 1
