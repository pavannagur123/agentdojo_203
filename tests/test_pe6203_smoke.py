"""Keyless smoke tests for the PE6203 AgentDojo development environment."""

from agentdojo.agent_pipeline.tool_execution import ToolsExecutor
from agentdojo.functions_runtime import EmptyEnv, FunctionCall, FunctionsRuntime
from agentdojo.task_suite.load_suites import get_suites
from agentdojo.types import ChatAssistantMessage


def test_current_benchmark_suites_load() -> None:
    suites = get_suites("v1.2.2")

    assert set(suites) == {"banking", "slack", "travel", "workspace"}
    assert all(suite.user_tasks for suite in suites.values())
    assert all(suite.injection_tasks for suite in suites.values())


def test_tool_execution_pipeline_runs_without_model_credentials() -> None:
    runtime = FunctionsRuntime()

    @runtime.register_function
    def add(a: int, b: int) -> int:
        """Add two integers.

        :param a: First integer.
        :param b: Second integer.
        """
        return a + b

    tool_call = FunctionCall(function="add", args={"a": 2, "b": 3}, id="smoke-call")
    assistant_message = ChatAssistantMessage(role="assistant", content=None, tool_calls=[tool_call])

    _, _, _, messages, _ = ToolsExecutor().query(
        query="Add two numbers",
        runtime=runtime,
        env=EmptyEnv(),
        messages=[assistant_message],
    )

    result = messages[-1]
    assert result["role"] == "tool"
    assert result["tool_call_id"] == "smoke-call"
    assert result["content"] == [{"type": "text", "content": "5"}]
    assert result["error"] is None
