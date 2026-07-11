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


def test_empty_results_render_hint_and_attribution() -> None:
    blocks = grant_results("", [])
    assert len(blocks) == 2
    assert "No currently actionable grants matched" in str(blocks[0])


def test_results_disclose_required_grants_gov_attribution() -> None:
    grant = Grant("1", "T", "A", date(2027, 3, 2), "https://g/1").to_dict()
    rendered = "\n".join(str(block) for block in grant_results("Match.", [grant]))
    assert "This product uses the Grants.gov API" in rendered
    assert "not an eligibility determination" in rendered


def test_card_labels_actionability_and_grounded_evidence() -> None:
    grant = Grant(
        "1",
        "Youth Conservation",
        "DOI",
        date(2027, 3, 2),
        "https://g/1",
        status="posted",
    ).to_dict()
    grant.update(
        {
            "reason": "Supports youth conservation training",
            "evidence": "Youth Conservation Corps",
        }
    )
    rendered = "\n".join(str(block) for block in grant_results("Match.", [grant]))
    assert "Open · DOI · Closes" in rendered
    assert "AI rationale" in rendered
    assert "Source evidence" in rendered
