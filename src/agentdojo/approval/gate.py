"""BASIL policy enforcement point and append-only decision ledger."""

from collections.abc import Sequence

from agentdojo.approval.intent import RuleBasedIntentCompiler
from agentdojo.approval.metadata import infer_tool_metadata
from agentdojo.approval.models import (
    ApprovalDecision,
    ApprovalRecord,
    AuthorizationContract,
    GateResult,
    ReviewerDecision,
    ToolCallContext,
)
from agentdojo.approval.policies import ApprovalPolicy
from agentdojo.approval.provenance import infer_argument_origins
from agentdojo.approval.reviewers import ApprovalReviewer
from agentdojo.functions_runtime import FunctionCall
from agentdojo.types import ChatMessage


class ApprovalGate:
    """Evaluate calls, enforce the escalation budget, and retain evidence."""

    def __init__(
        self,
        policy: ApprovalPolicy,
        reviewer: ApprovalReviewer,
        escalation_budget: int,
        intent_compiler: RuleBasedIntentCompiler | None = None,
    ) -> None:
        if escalation_budget < 0:
            raise ValueError("escalation_budget must be non-negative")
        self.policy = policy
        self.reviewer = reviewer
        self.escalation_budget = escalation_budget
        self.intent_compiler = intent_compiler or RuleBasedIntentCompiler()
        self.contract: AuthorizationContract | None = None
        self.records: list[ApprovalRecord] = []
        self.escalations_used = 0

    def start_task(self, query: str) -> None:
        """Reset per-task state and compile authority from trusted input only."""

        self.contract = self.intent_compiler.compile(query)
        self.records = []
        self.escalations_used = 0

    def decide(
        self,
        query: str,
        tool_call: FunctionCall,
        tool_description: str,
        messages: Sequence[ChatMessage],
    ) -> GateResult:
        if self.contract is None:
            self.start_task(query)
        assert self.contract is not None
        metadata = infer_tool_metadata(tool_call.function, tool_description)
        origins = infer_argument_origins(dict(tool_call.args), query, messages)
        context = ToolCallContext(
            query=query,
            function=tool_call.function,
            arguments=dict(tool_call.args),
            tool_description=tool_description,
            metadata=metadata,
            argument_origins=origins,
            contract=self.contract,
        )
        policy_decision = self.policy.decide(context)
        final_decision = policy_decision.decision
        reason = policy_decision.reason
        reviewer_decision = None

        if policy_decision.decision == ApprovalDecision.ESCALATE:
            if self.escalations_used >= self.escalation_budget:
                final_decision = ApprovalDecision.DENY
                reason = f"Escalation budget exhausted ({self.escalation_budget}); fail-closed denial."
            else:
                self.escalations_used += 1
                try:
                    reviewer_decision = self.reviewer.review(context, policy_decision.reason)
                except Exception as error:
                    reviewer_decision = ReviewerDecision(
                        approved=False,
                        reason=f"Reviewer failed with {type(error).__name__}; fail-closed denial.",
                    )
                final_decision = ApprovalDecision.APPROVE if reviewer_decision.approved else ApprovalDecision.DENY
                reason = (
                    f"Reviewer {'approved' if reviewer_decision.approved else 'denied'}: {reviewer_decision.reason}"
                )

        record = ApprovalRecord(
            sequence=len(self.records) + 1,
            function=tool_call.function,
            arguments=dict(tool_call.args),
            argument_origins=origins,
            effects=metadata.effects,
            risk=metadata.risk,
            policy_decision=policy_decision.decision,
            final_decision=final_decision,
            reason=reason,
            matched_clause_ids=policy_decision.matched_clause_ids,
            escalations_used=self.escalations_used,
            escalation_budget=self.escalation_budget,
            reviewer_reason=reviewer_decision.reason if reviewer_decision is not None else None,
            reviewer_input_tokens=reviewer_decision.input_tokens if reviewer_decision is not None else 0,
            reviewer_output_tokens=reviewer_decision.output_tokens if reviewer_decision is not None else 0,
            reviewer_estimated_cost_usd=(
                reviewer_decision.estimated_cost_usd if reviewer_decision is not None else 0.0
            ),
        )
        self.records.append(record)
        return GateResult(decision=final_decision, reason=reason, record=record)

    def snapshot(self) -> dict:
        """Return JSON-serializable task evidence for benchmark traces."""

        return {
            "policy": self.policy.name,
            "reviewer": self.reviewer.name,
            "escalation_budget": self.escalation_budget,
            "escalations_used": self.escalations_used,
            "contract": self.contract.model_dump(mode="json") if self.contract is not None else None,
            "decisions": [record.model_dump(mode="json") for record in self.records],
        }
