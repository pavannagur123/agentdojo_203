"""Run a keyless, ground-truth-assisted static audit of BASIL policy coverage.

This is an offline development diagnostic. Ground truth is never supplied to
the runtime policy or simulated reviewer during actual benchmark experiments.
"""

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any

from agentdojo.approval.gate import ApprovalGate
from agentdojo.approval.metadata import infer_tool_metadata
from agentdojo.approval.policies import BasilPolicy
from agentdojo.approval.reviewers import DeterministicReviewer
from agentdojo.functions_runtime import FunctionCall
from agentdojo.task_suite.load_suites import get_suites
from agentdojo.types import ChatToolResultMessage, text_content_block_from_string


def run_static_audit(benchmark_version: str = "v1.2.2") -> dict[str, Any]:
    report: dict[str, Any] = {"benchmark_version": benchmark_version, "suites": {}}
    for suite_name, suite in get_suites(benchmark_version).items():
        tools = {tool.name: tool for tool in suite.tools}
        base_environment = suite.load_and_inject_default_environment({})
        legitimate_counts: Counter[str] = Counter()
        denied_legitimate = []
        for task in suite.user_tasks.values():
            environment = task.init_environment(base_environment.model_copy(deep=True))
            gate = ApprovalGate(BasilPolicy(), DeterministicReviewer(), escalation_budget=10_000)
            gate.start_task(task.PROMPT)
            for call in task.ground_truth(environment):
                result = gate.decide(task.PROMPT, call, tools[call.function].description, [])
                decision = result.record.policy_decision.value
                legitimate_counts[decision] += 1
                if decision == "deny":
                    denied_legitimate.append({"user_task": task.ID, "function": call.function, "reason": result.reason})

        proxy_counts: Counter[str] = Counter()
        for task in suite.user_tasks.values():
            for injection_task in suite.injection_tasks.values():
                gate = ApprovalGate(BasilPolicy(), DeterministicReviewer(), escalation_budget=10_000)
                gate.start_task(task.PROMPT)
                for call in injection_task.ground_truth(base_environment.model_copy(deep=True)):
                    if call.function not in tools:
                        continue
                    tool = tools[call.function]
                    metadata = infer_tool_metadata(call.function, tool.description)
                    if not metadata.has_side_effect:
                        continue
                    source_call = FunctionCall(function="untrusted_source", args={}, id="static-source")
                    simulated_untrusted_output = ChatToolResultMessage(
                        role="tool",
                        content=[text_content_block_from_string(json.dumps(call.args, default=str))],
                        tool_call_id=source_call.id,
                        tool_call=source_call,
                        error=None,
                    )
                    result = gate.decide(task.PROMPT, call, tool.description, [simulated_untrusted_output])
                    proxy_counts[result.record.policy_decision.value] += 1

        proxy_total = sum(proxy_counts.values())
        report["suites"][suite_name] = {
            "legitimate_policy_decisions": dict(legitimate_counts),
            "denied_legitimate_calls": denied_legitimate,
            "malicious_side_effect_proxy_decisions": dict(proxy_counts),
            "malicious_side_effect_proxy_auto_approve_rate": (
                proxy_counts["approve"] / proxy_total if proxy_total else 0.0
            ),
        }
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--benchmark-version", default="v1.2.2")
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()
    report = run_static_audit(args.benchmark_version)
    serialized = json.dumps(report, indent=2, sort_keys=True)
    if args.output is None:
        print(serialized)
    else:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(serialized)
        print(f"Wrote {args.output}")


if __name__ == "__main__":
    main()
