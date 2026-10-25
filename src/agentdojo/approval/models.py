"""Shared data models for the BASIL approval gate.

These models deliberately live outside the original AgentDojo pipeline so the
project extension has a small and auditable integration surface.
"""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from agentdojo.strenum import StrEnum


class ApprovalDecision(StrEnum):
    """The three decisions required by the PE6203 project brief."""

    APPROVE = "approve"
    DENY = "deny"
    ESCALATE = "escalate"


class ArgumentOrigin(StrEnum):
    """The most trusted source in which a tool argument was observed."""

    USER = "user"
    TOOL = "tool"
    AGENT = "agent"


class ToolEffect(StrEnum):
    """Observable effects a tool can have on the simulated environment."""

    READ = "read"
    WRITE = "write"
    DELETE = "delete"
    COMMUNICATE = "communicate"
    FINANCIAL = "financial"
    PERMISSION = "permission"
    AUTHENTICATION = "authentication"
    EXTERNAL = "external"


class RiskLevel(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AuthorizationClause(BaseModel):
    """One auditable clause derived from the user's original request."""

    clause_id: str
    text: str
    tokens: set[str] = Field(default_factory=set)
    prohibited: bool = False


class AuthorizationContract(BaseModel):
    """Immutable task authority compiled only from trusted user input."""

    original_request: str
    clauses: tuple[AuthorizationClause, ...]


class ToolMetadata(BaseModel):
    """Security-relevant description of a tool's possible effects."""

    name: str
    description: str = ""
    effects: frozenset[ToolEffect]
    risk: RiskLevel
    operation_terms: frozenset[str] = frozenset()
    action_terms: frozenset[str] = frozenset()

    @property
    def is_read_only(self) -> bool:
        return self.effects == frozenset({ToolEffect.READ})

    @property
    def has_side_effect(self) -> bool:
        return any(effect != ToolEffect.READ for effect in self.effects)


class ToolCallContext(BaseModel):
    """Information available to a policy at the pre-execution boundary."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    query: str
    function: str
    arguments: dict[str, Any]
    tool_description: str
    metadata: ToolMetadata
    argument_origins: dict[str, ArgumentOrigin]
    contract: AuthorizationContract


class PolicyDecision(BaseModel):
    """A policy's recommendation before any human-review simulation."""

    decision: ApprovalDecision
    reason: str
    matched_clause_ids: tuple[str, ...] = ()
    risk_score: float = Field(ge=0.0, le=1.0)


class ReviewerDecision(BaseModel):
    """The simulated reviewer's response to an escalation."""

    approved: bool
    reason: str
    input_tokens: int = 0
    output_tokens: int = 0
    estimated_cost_usd: float = 0.0


class ApprovalRecord(BaseModel):
    """Append-only evidence for one tool-call decision."""

    sequence: int
    function: str
    arguments: dict[str, Any]
    argument_origins: dict[str, ArgumentOrigin]
    effects: frozenset[ToolEffect]
    risk: RiskLevel
    policy_decision: ApprovalDecision
    final_decision: ApprovalDecision
    reason: str
    matched_clause_ids: tuple[str, ...] = ()
    escalations_used: int
    escalation_budget: int
    reviewer_reason: str | None = None
    reviewer_input_tokens: int = 0
    reviewer_output_tokens: int = 0
    reviewer_estimated_cost_usd: float = 0.0


class GateResult(BaseModel):
    """The final executable decision returned by BASIL."""

    decision: ApprovalDecision
    reason: str
    record: ApprovalRecord
