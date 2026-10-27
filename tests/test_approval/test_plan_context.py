from agentdojo.agent_pipeline.tool_execution import ToolsExecutor
from agentdojo.approval.gate import ApprovalGate
from agentdojo.approval.intent import OpenAICompatibleIntentCompiler, RuleBasedIntentCompiler
from agentdojo.approval.plan_context import AuthorizationPlanContext
from agentdojo.approval.policies import FullApprovePolicy
from agentdojo.functions_runtime import FunctionCall, FunctionsRuntime
from agentdojo.types import ChatAssistantMessage


def test_planner_brief_is_dynamic_context_and_is_not_recompiled(fake_openai_client: object) -> None:
    fake_openai_client.chat.completions.queue_payload(  # type: ignore[attr-defined]
        {
            "clauses": [
                {
                    "text": "Send a summary to Alice",
                    "prohibited": False,
                    "action": "send a summary",
                    "targets": ["Alice"],
                    "allowed_data_sources": ["calendar"],
                    "required_facts": ["Alice's address", "the event time"],
                    "success_criteria": ["The summary is sent once to Alice"],
                    "max_executions": 1,
                }
            ]
        }
    )
    compiler = OpenAICompatibleIntentCompiler(fake_openai_client, "test/planner")  # type: ignore[arg-type]
    gate = ApprovalGate(FullApprovePolicy(), reviewer=None, escalation_budget=0, intent_compiler=compiler)
    context = AuthorizationPlanContext(gate)

    query, runtime, env, messages, extra_args = context.query(
        "Send Alice a summary of the calendar event",
        FunctionsRuntime(),
    )

    assert len(fake_openai_client.chat.completions.calls) == 1  # type: ignore[attr-defined]
    assert messages[-1]["role"] == "system"
    brief = messages[-1]["content"][0]["content"]
    assert "planning aid, not a new source of authority" in brief
    assert "Alice's address" in brief
    assert "The summary is sent once to Alice" in brief
    assert extra_args["approval_plan_initialized"] is True
    assert extra_args["basil"]["contract"]["planner_model"] == "test/planner"

    proposed_call = ChatAssistantMessage(
        role="assistant",
        content=None,
        tool_calls=[FunctionCall(function="missing_tool", args={}, id="call-1")],
    )
    ToolsExecutor(approval_gate=gate).query(
        query,
        runtime,
        env,
        [*messages, proposed_call],
        extra_args,
    )

    assert len(fake_openai_client.chat.completions.calls) == 1  # type: ignore[attr-defined]


def test_rule_based_fallback_is_not_promoted_into_agent_context() -> None:
    gate = ApprovalGate(
        FullApprovePolicy(),
        reviewer=None,
        escalation_budget=0,
        intent_compiler=RuleBasedIntentCompiler(),
    )

    _, _, _, messages, extra_args = AuthorizationPlanContext(gate).query(
        "Read my calendar",
        FunctionsRuntime(),
    )

    assert messages == []
    assert extra_args["approval_plan_initialized"] is True
    assert extra_args["basil"]["contract"]["planner_model"] is None
