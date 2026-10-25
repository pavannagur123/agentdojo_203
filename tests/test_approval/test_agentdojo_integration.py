import json
from collections.abc import Sequence
from pathlib import Path

from agentdojo.agent_pipeline import AgentPipeline, BasePipelineElement, PipelineConfig
from agentdojo.benchmark import run_task_without_injection_tasks
from agentdojo.functions_runtime import EmptyEnv, Env, FunctionCall, FunctionsRuntime
from agentdojo.logging import OutputLogger
from agentdojo.task_suite.load_suites import get_suite
from agentdojo.types import ChatAssistantMessage, ChatMessage, text_content_block_from_string


class ScriptedWorkspaceAgent(BasePipelineElement):
    """Keyless agent that completes one real AgentDojo workspace task."""

    name = "scripted-workspace-agent"

    def query(
        self,
        query: str,
        runtime: FunctionsRuntime,
        env: Env = EmptyEnv(),
        messages: Sequence[ChatMessage] = [],
        extra_args: dict = {},
    ) -> tuple[str, FunctionsRuntime, Env, Sequence[ChatMessage], dict]:
        if any(message["role"] == "tool" for message in messages):
            answer = "networking.participants@industry-network.com alex.williams@mainsail-tech.com"
            output = ChatAssistantMessage(
                role="assistant",
                content=[text_content_block_from_string(answer)],
                tool_calls=None,
            )
        else:
            output = ChatAssistantMessage(
                role="assistant",
                content=None,
                tool_calls=[
                    FunctionCall(
                        function="search_calendar_events",
                        args={"query": "Networking event", "date": "2024-05-26"},
                        id="lookup",
                    )
                ],
            )
        return query, runtime, env, [*messages, output], extra_args


def test_basil_completes_real_agentdojo_task_and_logs_ledger(tmp_path: Path) -> None:
    suite = get_suite("v1.2.2", "workspace")
    task = suite.get_user_task_by_id("user_task_0")
    pipeline = AgentPipeline.from_config(
        PipelineConfig(
            llm=ScriptedWorkspaceAgent(),
            model_id=None,
            defense=None,
            tool_delimiter="tool",
            system_message_name=None,
            system_message=None,
            approval_policy="basil",
            approval_budget=1,
        )
    )

    with OutputLogger(str(tmp_path)):
        utility, security = run_task_without_injection_tasks(
            suite,
            pipeline,
            task,
            logdir=tmp_path,
            force_rerun=True,
            benchmark_version="v1.2.2",
        )

    trace_path = (
        tmp_path / "scripted-workspace-agent-approval-basil-k1" / "workspace" / "user_task_0" / "none" / "none.json"
    )
    trace = json.loads(trace_path.read_text())

    assert utility is True
    assert security is True
    assert trace["basil"]["policy"] == "basil"
    assert trace["basil"]["decisions"][0]["function"] == "search_calendar_events"
    assert trace["basil"]["decisions"][0]["final_decision"] == "approve"
