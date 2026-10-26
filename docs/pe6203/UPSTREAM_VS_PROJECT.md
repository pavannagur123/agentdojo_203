# Upstream AgentDojo versus the PE6203 project

The repository started from ETH Zurich AgentDojo 0.1.35. The benchmark suites, simulated tools, attacks, task evaluators, model adapters, and existing defenses remain the upstream foundation.

| Area | Upstream AgentDojo | PE6203 addition |
| --- | --- | --- |
| Tool execution | Executes every valid call | Optional pre-execution approval hook |
| Decisions | No approve/deny/escalate decision | Three-way BASIL decision model |
| Authority | Agent decides which tools to request | Contract compiled from the trusted user request |
| Provenance | Tool arguments are not assigned trust origins | User/tool/agent argument-origin labels |
| Risk | Tools expose schemas and descriptions | Deterministic effect and risk classification |
| Human review | No budgeted simulated reviewer | Required LLM-simulated human reviewer for escalating policies |
| Budget | No escalation budget | Per-task budget `k`, followed by fail-closed denial |
| Evidence | Conversation and benchmark result traces | Append-only authorization decision ledger |
| Baselines | Undefended and existing prompt-injection defenses | Full-approve and full-escalate approval baselines |

## Files added by this project

- `src/agentdojo/approval/`: BASIL models, intent compiler, metadata, provenance, policies, reviewers, gate, and metrics.
- `tests/test_approval/`: approval-specific unit and integration tests.
- `docs/pe6203/`: design, differentiation, and testing documentation.
- `.env.example`: secret-free local configuration template.

## Minimal upstream integration surface

Only three existing runtime files are intentionally extended:

1. `agent_pipeline/tool_execution.py` calls the optional gate before `runtime.run_function`.
2. `agent_pipeline/agent_pipeline.py` constructs the optional gate from configuration.
3. `scripts/benchmark.py` exposes the configuration as command-line options.
4. `agent_pipeline/llms/openai_llm.py` records actual agent token usage and provider-reported cost for experiments.

When `approval_policy` is unset, no gate is created and the original execution path is retained. This disabled mode is tested explicitly and is the upstream-behaviour control for experiments.
