import json
from pathlib import Path
from types import SimpleNamespace

from agentdojo.approval.report import aggregate_traces, load_traces
from agentdojo.approval.usage import extract_usage


def test_report_aggregates_task_security_hitl_and_cost(tmp_path: Path) -> None:
    trace = {
        "pipeline_name": "model-approval-basil-k1",
        "suite_name": "workspace",
        "user_task_id": "user_task_0",
        "injection_task_id": "injection_task_0",
        "attack_type": "tool_knowledge",
        "utility": True,
        "security": False,
        "agent_usage": {"input_tokens": 100, "output_tokens": 20, "cost_usd": 0.01},
        "basil": {
            "policy": "basil",
            "reviewer": "openai-compatible",
            "escalation_budget": 1,
            "decisions": [
                {
                    "function": "send_email",
                    "policy_decision": "escalate",
                    "final_decision": "approve",
                    "reviewer_reason": "authorized",
                    "reviewer_input_tokens": 30,
                    "reviewer_output_tokens": 5,
                    "reviewer_estimated_cost_usd": 0.002,
                }
            ],
        },
    }
    trace_path = tmp_path / "run.json"
    trace_path.write_text(json.dumps(trace))

    report = aggregate_traces(load_traces(tmp_path))
    summary = report["summary"][0]

    assert summary["task_completion_rate"] == 1.0
    assert summary["attack_success_rate"] == 0.0
    assert summary["safe_task_completion_rate"] == 1.0
    assert summary["average_human_reviews_per_task"] == 1.0
    assert summary["hitl_call_rate"] == 1.0
    assert summary["total_cost_usd"] == 0.012


def test_report_marks_failure_trajectories(tmp_path: Path) -> None:
    trace = {
        "pipeline_name": "model-approval-basil-k0",
        "suite_name": "workspace",
        "user_task_id": "user_task_0",
        "injection_task_id": "injection_task_0",
        "attack_type": "tool_knowledge",
        "utility": False,
        "security": True,
        "basil": {"policy": "basil", "reviewer": "openai-compatible", "escalation_budget": 0, "decisions": []},
    }
    (tmp_path / "failure.json").write_text(json.dumps(trace))

    report = aggregate_traces(load_traces(tmp_path))

    assert report["failures"][0]["type"] == "over-permissive"


def test_usage_extracts_provider_cost() -> None:
    completion = SimpleNamespace(
        usage=SimpleNamespace(
            prompt_tokens=10,
            completion_tokens=3,
            total_tokens=13,
            model_extra={"cost": 0.004},
        )
    )

    assert extract_usage(completion) == {
        "input_tokens": 10,
        "output_tokens": 3,
        "total_tokens": 13,
        "cost_usd": 0.004,
    }
