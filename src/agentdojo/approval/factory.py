"""Configuration factory for command-line and programmatic BASIL use."""

import os
from typing import Literal

from openai import OpenAI

from agentdojo.approval.gate import ApprovalGate
from agentdojo.approval.intent import OpenAICompatibleIntentCompiler
from agentdojo.approval.policies import BasilPolicy, FullApprovePolicy, FullEscalatePolicy
from agentdojo.approval.reviewers import OpenAICompatibleReviewer

ApprovalPolicyName = Literal["full-approve", "full-escalate", "basil"]

APPROVAL_POLICIES: tuple[ApprovalPolicyName, ...] = ("full-approve", "full-escalate", "basil")


def build_approval_gate(
    policy_name: ApprovalPolicyName,
    escalation_budget: int,
    reviewer_model: str | None = None,
    planner_model: str | None = None,
) -> ApprovalGate:
    policies = {
        "full-approve": FullApprovePolicy(),
        "full-escalate": FullEscalatePolicy(),
        "basil": BasilPolicy(),
    }
    if policy_name == "full-approve":
        return ApprovalGate(policies[policy_name], None, escalation_budget)

    base_url = os.getenv("OPENAI_COMPATIBLE_BASE_URL")
    api_key = os.getenv("OPENAI_COMPATIBLE_API_KEY")
    reviewer_model = reviewer_model or os.getenv("OPENAI_COMPATIBLE_REVIEWER_MODEL")
    missing = [
        name
        for name, value in (
            ("OPENAI_COMPATIBLE_BASE_URL", base_url),
            ("OPENAI_COMPATIBLE_API_KEY", api_key),
            ("--approval-reviewer-model or OPENAI_COMPATIBLE_REVIEWER_MODEL", reviewer_model),
        )
        if not value
    ]
    if missing:
        raise ValueError(
            f"Approval policy '{policy_name}' can escalate and requires the LLM-simulated human reviewer. "
            f"Missing configuration: {', '.join(missing)}."
        )
    assert base_url is not None and api_key is not None and reviewer_model is not None
    client = OpenAI(base_url=base_url, api_key=api_key)
    reviewer = OpenAICompatibleReviewer(client, reviewer_model)
    planner_model = planner_model or os.getenv("OPENAI_COMPATIBLE_APPROVAL_PLANNER_MODEL")
    planner = OpenAICompatibleIntentCompiler(client, planner_model) if planner_model else None
    return ApprovalGate(policies[policy_name], reviewer, escalation_budget, intent_compiler=planner)
