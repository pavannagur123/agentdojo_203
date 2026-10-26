from typing import Any

import pytest

from agentdojo.approval.factory import build_approval_gate
from agentdojo.approval.models import ApprovalDecision
from agentdojo.functions_runtime import FunctionCall


def _clear_reviewer_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in (
        "OPENAI_COMPATIBLE_BASE_URL",
        "OPENAI_COMPATIBLE_API_KEY",
        "OPENAI_COMPATIBLE_REVIEWER_MODEL",
    ):
        monkeypatch.delenv(name, raising=False)


@pytest.mark.parametrize("policy", ["basil", "full-escalate"])
def test_escalating_policy_fails_fast_without_llm_configuration(
    monkeypatch: pytest.MonkeyPatch,
    policy: Any,
) -> None:
    _clear_reviewer_environment(monkeypatch)

    with pytest.raises(ValueError, match="can escalate.*LLM-simulated human reviewer"):
        build_approval_gate(policy, escalation_budget=1)


def test_full_approve_needs_no_reviewer_configuration(monkeypatch: pytest.MonkeyPatch) -> None:
    _clear_reviewer_environment(monkeypatch)

    gate = build_approval_gate("full-approve", escalation_budget=0)

    assert gate.snapshot()["reviewer"] is None
    assert gate.snapshot()["reviewer_model"] is None


def test_llm_reviewer_uses_json_temperature_zero_and_records_model(
    configured_llm_reviewer: Any,
) -> None:
    gate = build_approval_gate("full-escalate", escalation_budget=1)
    query = "Send Alice an email"
    call = FunctionCall(function="send_email", args={"address": "alice@example.com"})
    gate.start_task(query)

    result = gate.decide(query, call, "Send an email", [])

    assert result.decision == ApprovalDecision.APPROVE
    assert result.record.reviewer_model == "test/reviewer-model"
    assert gate.snapshot()["reviewer_model"] == "test/reviewer-model"
    request = configured_llm_reviewer.chat.completions.calls[0]
    assert request["model"] == "test/reviewer-model"
    assert request["temperature"] == 0
    assert request["response_format"] == {"type": "json_object"}
