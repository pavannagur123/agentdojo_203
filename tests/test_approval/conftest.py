import json
from types import SimpleNamespace
from typing import Any

import pytest

from agentdojo.approval.reviewers import OpenAICompatibleReviewer


class FakeCompletions:
    def __init__(self) -> None:
        self.decisions: list[dict[str, Any]] = []
        self.calls: list[dict[str, Any]] = []

    def queue(self, approved: bool, reason: str = "Canned reviewer decision.") -> None:
        self.decisions.append({"approved": approved, "reason": reason})

    def create(self, **kwargs: Any) -> Any:
        self.calls.append(kwargs)
        decision = self.decisions.pop(0) if self.decisions else {
            "approved": True,
            "reason": "Canned reviewer approval.",
        }
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content=json.dumps(decision)))],
            usage=SimpleNamespace(
                prompt_tokens=11,
                completion_tokens=4,
                total_tokens=15,
                model_extra={"cost": 0.0},
            ),
        )


class FakeOpenAIClient:
    def __init__(self) -> None:
        self.base_url = "https://mock-openai.invalid/v1"
        self.chat = SimpleNamespace(completions=FakeCompletions())


@pytest.fixture
def fake_openai_client() -> FakeOpenAIClient:
    return FakeOpenAIClient()


@pytest.fixture
def llm_reviewer(fake_openai_client: FakeOpenAIClient) -> OpenAICompatibleReviewer:
    return OpenAICompatibleReviewer(fake_openai_client, "test/reviewer-model")  # type: ignore[arg-type]


@pytest.fixture
def configured_llm_reviewer(
    monkeypatch: pytest.MonkeyPatch,
    fake_openai_client: FakeOpenAIClient,
) -> FakeOpenAIClient:
    monkeypatch.setenv("OPENAI_COMPATIBLE_BASE_URL", "https://mock-openai.invalid/v1")
    monkeypatch.setenv("OPENAI_COMPATIBLE_API_KEY", "test-key-not-a-secret")
    monkeypatch.setenv("OPENAI_COMPATIBLE_REVIEWER_MODEL", "test/reviewer-model")
    monkeypatch.setattr("agentdojo.approval.factory.OpenAI", lambda **_: fake_openai_client)
    return fake_openai_client
