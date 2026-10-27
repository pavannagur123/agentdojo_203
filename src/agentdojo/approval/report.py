"""Aggregate AgentDojo JSON traces into PE6203 experiment metrics."""

import json
from collections import defaultdict
from pathlib import Path
from typing import Any


def _rate(numerator: int, denominator: int) -> float | None:
    return numerator / denominator if denominator else None


def load_traces(root: Path) -> list[tuple[Path, dict[str, Any]]]:
    traces = []
    for path in sorted(root.rglob("*.json")):
        try:
            value = json.loads(path.read_text())
        except (json.JSONDecodeError, OSError):
            continue
        if isinstance(value, dict) and "pipeline_name" in value and "utility" in value:
            traces.append((path, value))
    return traces


def aggregate_traces(traces: list[tuple[Path, dict[str, Any]]]) -> dict[str, Any]:
    """Return grouped rates, load/cost metrics, and inspectable failures."""

    groups: dict[tuple[Any, ...], dict[str, Any]] = defaultdict(
        lambda: {
            "tasks": 0,
            "utility_successes": 0,
            "attacked_tasks": 0,
            "attack_successes": 0,
            "safe_completions": 0,
            "tool_calls": 0,
            "approved_calls": 0,
            "denied_calls": 0,
            "human_reviews": 0,
            "successful_task_human_reviews": 0,
            "agent_input_tokens": 0,
            "agent_output_tokens": 0,
            "reviewer_input_tokens": 0,
            "reviewer_output_tokens": 0,
            "planner_input_tokens": 0,
            "planner_output_tokens": 0,
            "agent_cost_usd": 0.0,
            "reviewer_cost_usd": 0.0,
            "planner_cost_usd": 0.0,
        }
    )
    effect_groups: dict[tuple[Any, ...], dict[str, Any]] = defaultdict(
        lambda: {
            "tool_calls": 0,
            "escalations": 0,
            "human_reviews": 0,
            "reviewer_approvals": 0,
            "reviewer_denials": 0,
            "final_approvals": 0,
            "final_denials": 0,
        }
    )
    failures = []

    for path, trace in traces:
        basil = trace.get("basil") or {}
        policy = basil.get("policy", "disabled")
        reviewer = basil.get("reviewer", "none")
        budget = basil.get("escalation_budget")
        attack_type = trace.get("attack_type") or "none"
        key = (trace.get("pipeline_name"), trace.get("suite_name"), attack_type, policy, reviewer, budget)
        group = groups[key]
        decisions = basil.get("decisions") or []
        utility = bool(trace.get("utility"))
        attacked = attack_type != "none"
        attack_success = attacked and bool(trace.get("security"))
        safe_completion = utility and not attack_success
        actual_reviews = sum(decision.get("reviewer_reason") is not None for decision in decisions)

        group["tasks"] = int(group["tasks"]) + 1
        group["utility_successes"] = int(group["utility_successes"]) + int(utility)
        group["attacked_tasks"] = int(group["attacked_tasks"]) + int(attacked)
        group["attack_successes"] = int(group["attack_successes"]) + int(attack_success)
        group["safe_completions"] = int(group["safe_completions"]) + int(safe_completion)
        group["tool_calls"] = int(group["tool_calls"]) + len(decisions)
        group["approved_calls"] = int(group["approved_calls"]) + sum(
            decision.get("final_decision") == "approve" for decision in decisions
        )
        group["denied_calls"] = int(group["denied_calls"]) + sum(
            decision.get("final_decision") == "deny" for decision in decisions
        )
        group["human_reviews"] = int(group["human_reviews"]) + actual_reviews
        if safe_completion:
            group["successful_task_human_reviews"] = (
                int(group["successful_task_human_reviews"]) + actual_reviews
            )

        for decision in decisions:
            effects = decision.get("effects") or ["unknown"]
            for effect in effects:
                effect_key = (*key, str(effect))
                effect_group = effect_groups[effect_key]
                reviewed = decision.get("reviewer_reason") is not None
                escalated = decision.get("policy_decision") == "escalate"
                approved = decision.get("final_decision") == "approve"
                effect_group["tool_calls"] = int(effect_group["tool_calls"]) + 1
                effect_group["escalations"] = int(effect_group["escalations"]) + int(escalated)
                effect_group["human_reviews"] = int(effect_group["human_reviews"]) + int(reviewed)
                effect_group["reviewer_approvals"] = int(effect_group["reviewer_approvals"]) + int(
                    reviewed and approved
                )
                effect_group["reviewer_denials"] = int(effect_group["reviewer_denials"]) + int(
                    reviewed and not approved
                )
                effect_group["final_approvals"] = int(effect_group["final_approvals"]) + int(approved)
                effect_group["final_denials"] = int(effect_group["final_denials"]) + int(not approved)

        agent_usage = trace.get("agent_usage") or {}
        group["agent_input_tokens"] = int(group["agent_input_tokens"]) + int(agent_usage.get("input_tokens", 0))
        group["agent_output_tokens"] = int(group["agent_output_tokens"]) + int(agent_usage.get("output_tokens", 0))
        group["agent_cost_usd"] = float(group["agent_cost_usd"]) + float(agent_usage.get("cost_usd", 0.0))
        group["reviewer_input_tokens"] = int(group["reviewer_input_tokens"]) + sum(
            int(decision.get("reviewer_input_tokens", 0)) for decision in decisions
        )
        group["reviewer_output_tokens"] = int(group["reviewer_output_tokens"]) + sum(
            int(decision.get("reviewer_output_tokens", 0)) for decision in decisions
        )
        group["reviewer_cost_usd"] = float(group["reviewer_cost_usd"]) + sum(
            float(decision.get("reviewer_estimated_cost_usd", 0.0)) for decision in decisions
        )
        contract = basil.get("contract") or {}
        group["planner_input_tokens"] = int(group["planner_input_tokens"]) + int(
            contract.get("planner_input_tokens", 0)
        )
        group["planner_output_tokens"] = int(group["planner_output_tokens"]) + int(
            contract.get("planner_output_tokens", 0)
        )
        group["planner_cost_usd"] = float(group["planner_cost_usd"]) + float(
            contract.get("planner_estimated_cost_usd", 0.0)
        )

        failure_type = None
        if attack_success:
            failure_type = "over-permissive"
        elif not utility and any(decision.get("final_decision") == "deny" for decision in decisions):
            failure_type = "possibly-over-conservative"
        if failure_type is not None:
            failures.append(
                {
                    "type": failure_type,
                    "trace": str(path),
                    "pipeline": trace.get("pipeline_name"),
                    "suite": trace.get("suite_name"),
                    "user_task": trace.get("user_task_id"),
                    "injection_task": trace.get("injection_task_id"),
                    "decisions": decisions,
                }
            )

    summaries = []
    for key, values in sorted(groups.items(), key=lambda item: tuple(str(value) for value in item[0])):
        pipeline, suite, attack_type, policy, reviewer, budget = key
        tasks = int(values["tasks"])
        attacked_tasks = int(values["attacked_tasks"])
        tool_calls = int(values["tool_calls"])
        human_reviews = int(values["human_reviews"])
        successful_task_human_reviews = int(values["successful_task_human_reviews"])
        safe_completions = int(values["safe_completions"])
        summaries.append(
            {
                "pipeline": pipeline,
                "suite": suite,
                "attack_type": attack_type,
                "approval_policy": policy,
                "reviewer": reviewer,
                "k": budget,
                **values,
                "task_completion_rate": _rate(int(values["utility_successes"]), tasks),
                "attack_success_rate": _rate(int(values["attack_successes"]), attacked_tasks),
                "safe_task_completion_rate": _rate(int(values["safe_completions"]), tasks),
                "average_human_reviews_per_task": _rate(human_reviews, tasks),
                "hitl_call_rate": _rate(human_reviews, tool_calls),
                "hitl_load_successful_tasks": successful_task_human_reviews,
                "average_human_reviews_per_safe_completion": _rate(
                    successful_task_human_reviews, safe_completions
                ),
                "total_cost_usd": (
                    float(values["agent_cost_usd"])
                    + float(values["reviewer_cost_usd"])
                    + float(values["planner_cost_usd"])
                ),
            }
        )

    curve_groups: dict[tuple[Any, ...], dict[str, int]] = defaultdict(
        lambda: {"tasks": 0, "safe_completions": 0, "human_reviews": 0, "hitl_load_successful_tasks": 0}
    )
    for summary in summaries:
        curve_key = (
            summary["attack_type"],
            summary["approval_policy"],
            summary["reviewer"],
            summary["k"],
        )
        curve_group = curve_groups[curve_key]
        for field in curve_group:
            curve_group[field] += int(summary[field])

    tcr_curves = []
    for key, values in sorted(curve_groups.items(), key=lambda item: tuple(str(value) for value in item[0])):
        attack_type, policy, reviewer, budget = key
        tcr_curves.append(
            {
                "attack_type": attack_type,
                "approval_policy": policy,
                "reviewer": reviewer,
                "k": budget,
                **values,
                "tcr_at_k": _rate(values["safe_completions"], values["tasks"]),
            }
        )

    escalation_value = []
    for key, values in sorted(effect_groups.items(), key=lambda item: tuple(str(value) for value in item[0])):
        pipeline, suite, attack_type, policy, reviewer, budget, effect = key
        human_reviews = int(values["human_reviews"])
        escalation_value.append(
            {
                "pipeline": pipeline,
                "suite": suite,
                "attack_type": attack_type,
                "approval_policy": policy,
                "reviewer": reviewer,
                "k": budget,
                "effect": effect,
                **values,
                "reviewer_approval_rate": _rate(int(values["reviewer_approvals"]), human_reviews),
            }
        )

    return {
        "summary": summaries,
        "tcr_curves": tcr_curves,
        "escalation_value": escalation_value,
        "failures": failures,
        "trace_count": len(traces),
    }
