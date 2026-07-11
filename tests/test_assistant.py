"""Assistant onboarding and cheap input validation."""

from __future__ import annotations

from types import SimpleNamespace

from grant_copilot.agent.orchestrator import AgentResult
from grant_copilot.slack.assistant import _greet, _make_reply


class _NeverCalledAgent:
    async def find(self, request, profile):  # pragma: no cover - failure path only
        raise AssertionError("blank messages must not call the agent")


class _ProfileRepo:
    def get(self, user_id):
        return None


class _Logger:
    def exception(self, message):
        raise AssertionError(message)


def test_greeting_sets_expectations_and_prompts() -> None:
    messages: list[str] = []
    captured_prompts: list[dict] = []

    def set_prompts(*, prompts: list[dict]) -> None:
        captured_prompts.extend(prompts)

    _greet(
        say=messages.append,
        set_suggested_prompts=set_prompts,
    )

    assert "profile-matched" in messages[0]
    assert "Home tab" in messages[0]
    assert len(captured_prompts) == 2


def test_blank_message_returns_guidance_without_calling_agent() -> None:
    messages: list[str] = []
    statuses: list[str] = []
    handler = _make_reply(_NeverCalledAgent(), _ProfileRepo())
    handler(
        payload={"text": "   "},
        context=SimpleNamespace(user_id="U1"),
        say=messages.append,
        set_status=statuses.append,
        logger=_Logger(),
    )

    assert messages == [
        "Tell me what your organization does or what kind of funding you need."
    ]


def test_empty_shortlist_uses_an_honest_accessible_fallback() -> None:
    class EmptyAgent:
        async def find(self, request, profile):
            return AgentResult(message="", grants=[])

    sent: list[dict] = []
    handler = _make_reply(EmptyAgent(), _ProfileRepo())
    handler(
        payload={"text": "A very specific need"},
        context=SimpleNamespace(user_id="U1"),
        say=lambda **kwargs: sent.append(kwargs),
        set_status=lambda status: None,
        logger=_Logger(),
    )

    assert sent[0]["text"] == "No currently actionable grants matched."
    assert "No currently actionable grants matched" in str(sent[0]["blocks"])
