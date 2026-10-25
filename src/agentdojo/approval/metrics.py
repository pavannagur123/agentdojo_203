"""Small, dependency-free summaries for BASIL decision ledgers."""

from collections import Counter

from agentdojo.approval.models import ApprovalDecision, ApprovalRecord


def summarize_decisions(records: list[ApprovalRecord]) -> dict[str, int | float]:
    counts = Counter(record.final_decision for record in records)
    escalated = sum(record.policy_decision == ApprovalDecision.ESCALATE for record in records)
    total = len(records)
    return {
        "total_calls": total,
        "approved": counts[ApprovalDecision.APPROVE],
        "denied": counts[ApprovalDecision.DENY],
        "escalated": escalated,
        "hitl_rate": escalated / total if total else 0.0,
        "reviewer_input_tokens": sum(record.reviewer_input_tokens for record in records),
        "reviewer_output_tokens": sum(record.reviewer_output_tokens for record in records),
        "reviewer_estimated_cost_usd": sum(record.reviewer_estimated_cost_usd for record in records),
    }
