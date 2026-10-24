# PE6203 AgentDojo Setup

This repository starts from ETH Zurich's AgentDojo `main` branch at commit
`089ed468cf3ed0322acc66b0211f26d9d90dbf60` (AgentDojo 0.1.35). It provides the
benchmark environment for NTU PE6203 Group Project 2, which will add a three-way
approval gate for agent tool calls: auto-approve, auto-deny, or escalate to a
simulated human reviewer under an escalation budget.

## Prerequisites

- Python 3.10, 3.11, or 3.12
- [uv](https://docs.astral.sh/uv/getting-started/installation/)
- Git

The repository includes `uv.lock`; use the locked dependencies so every group
member and CI runs the same environment.

## Install

From the repository root:

```bash
uv sync --frozen --dev
```

This creates `.venv` and installs AgentDojo in editable mode with the development
tools. No API key is needed to install the project or run the smoke tests.

## Configure model credentials

Only model-backed benchmark runs need a provider credential. Create a local file
from the safe template:

```bash
cp .env.example .env
```

Set only the variable required by the provider you use. For OpenAI, for example:

```dotenv
OPENAI_API_KEY=replace-with-your-local-key
```

`.env` is ignored by Git. Never add a real API key to source files, tests, command
history committed to the repository, workflow YAML, issues, or pull requests.

If a future GitHub Actions job runs model-backed tests, add the key in the GitHub
repository under **Settings > Secrets and variables > Actions**, name it
`OPENAI_API_KEY`, and reference it as `${{ secrets.OPENAI_API_KEY }}`. The current
smoke-test workflow is deliberately keyless and does not require this secret.

## Verify the installation

Run the project-specific, offline smoke tests:

```bash
uv run pytest tests/test_pe6203_smoke.py -q
```

Confirm that the benchmark command is installed:

```bash
uv run python -m agentdojo.scripts.benchmark --help
```

For a broader offline check, run the upstream test suite:

```bash
uv run pytest tests
```

Some upstream tests exercise provider adapters with mocked clients; they do not
make paid model calls. Actual benchmark commands do make model calls and therefore
require the relevant local environment variable.

## Run a small benchmark later

After configuring a key, a small unguarded AgentDojo run can be started with:

```bash
uv run python -m agentdojo.scripts.benchmark \
  --suite workspace \
  --user-task user_task_0 \
  --model gpt-4o-2024-05-13
```

This command can incur provider charges. It validates upstream benchmark execution;
it does not yet evaluate the PE6203 approval policy.

## Approval-gate integration point

AgentDojo constructs the default agent loop in
`src/agentdojo/agent_pipeline/agent_pipeline.py`. Tool requests are validated and
executed in `ToolsExecutor.query` in
`src/agentdojo/agent_pipeline/tool_execution.py`, immediately before
`runtime.run_function(...)`.

The next implementation stage should place the approval gate at that boundary so
every valid tool call is classified before it can mutate the task environment. The
gate will need to record the decision, reason, escalation count, and reviewer result
for the TCR@k, HITL-load, cost, and failure analyses required by the assignment.

## Keeping the fork current

The clone is configured with `origin` for this course repository and `upstream` for
ETH Zurich's repository. To inspect upstream updates without merging them:

```bash
git fetch upstream
git log --oneline main..upstream/main
```

Review upstream changes before merging because AgentDojo's public API is still under
development and changes may affect the approval-gate integration.
