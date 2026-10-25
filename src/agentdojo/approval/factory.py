"""Configuration factory for command-line and programmatic BASIL use."""

import os
from typing import Literal

from openai import OpenAI

from agentdojo.approval.gate import ApprovalGate
from agentdojo.approval.policies import BasilPolicy, FullApprovePolicy, FullEscalatePolicy
from agentdojo.approval.reviewers import DeterministicReviewer, OpenAICompatibleReviewer

ApprovalPolicyName = Literal["full-approve", "full-escalate", "basil"]
ReviewerName = Literal["deterministic", "openai-compatible"]

APPROVAL_POLICIES: tuple[ApprovalPolicyName, ...] = ("full-approve", "full-escalate", "basil")
APPROVAL_REVIEWERS: tuple[ReviewerName, ...] = ("deterministic", "openai-compatible")


def build_approval_gate(
    policy_name: ApprovalPolicyName,
    escalation_budget: int,
    reviewer_name: ReviewerName = "deterministic",
    reviewer_model: str | None = None,
) -> ApprovalGate:
    policies = {
        "full-approve": FullApprovePolicy(),
        "full-escalate": FullEscalatePolicy(),
        "basil": BasilPolicy(),
    }
    if reviewer_name == "deterministic":
        reviewer = DeterministicReviewer()
    else:
        base_url = os.getenv("OPENAI_COMPATIBLE_BASE_URL")
        api_key = os.getenv("OPENAI_COMPATIBLE_API_KEY")
        if not base_url or not api_key:
            raise ValueError(
                "OPENAI_COMPATIBLE_BASE_URL and OPENAI_COMPATIBLE_API_KEY are required for the LLM reviewer"
            )
        if reviewer_model is None:
            raise ValueError("A reviewer model is required for the LLM reviewer")
        reviewer = OpenAICompatibleReviewer(OpenAI(base_url=base_url, api_key=api_key), reviewer_model)
    return ApprovalGate(policies[policy_name], reviewer, escalation_budget)
