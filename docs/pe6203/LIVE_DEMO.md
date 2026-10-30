# Live presentation demo

This runner uses the real acting agent, Planner LLM, BASIL gate, and LLM
Reviewer through OpenRouter. It defaults all three LLM roles to
`openai/gpt-4.1` and keeps the review budget at two.

The tools operate only on AgentDojo's fixed synthetic sandbox. They do not
access live email, banking, Slack, travel, or calendar accounts. Consequently,
questions such as "What is the current date?" return the date stored in the
benchmark environment rather than the real-world date.

## One-time setup in the VS Code terminal

```bash
git clone https://github.com/pavannagur123/agentdojo_203.git
cd agentdojo_203
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e .
cp .env.example .env
code .env
```

In `.env`, add the OpenRouter key after `OPENAI_COMPATIBLE_API_KEY=`. Never
show the key on a slide, paste it into the terminal, or commit `.env`.

## Recommended scored demonstration

First list the official inputs:

```bash
python -m agentdojo.scripts.live_demo list-tasks --suite workspace
```

Then run one task. `workspace/user_task_18` is a clear demonstration because
the agent performs read-only discovery and then proposes a calendar write that
is escalated to the LLM Reviewer:

```bash
python -m agentdojo.scripts.live_demo task \
  --suite workspace \
  --task user_task_18
```

The terminal shows the exact input, agent/planner/reviewer models, PASS or FAIL,
the agent response, each proposed tool, risk, policy decision, final decision,
and the LLM Reviewer's reason. The full JSON trace is saved under
`runs/live-demo/`.

## Accept arbitrary input during questions

Run:

```bash
python -m agentdojo.scripts.live_demo prompt --suite workspace
```

The terminal asks `Enter the professor's input:`. The supplied text is passed
through the same Planner LLM, acting agent, tools, BASIL gate, and LLM Reviewer.
The terminal deliberately reports **not scored** rather than PASS or FAIL,
because a new prompt does not have an AgentDojo ground-truth evaluator. A JSON
record is still saved under `runs/live-demo/`.

You can select the available simulated tool environment with `--suite`:
`banking`, `slack`, `travel`, or `workspace`.

## Presentation safety checklist

- Put the API key in `.env` before presenting and keep that file closed.
- Confirm the internet connection and OpenRouter balance.
- Run the scored command once before the presentation to warm the environment.
- Add `--yes` to the scored command only if you want to skip its paid-run
  confirmation.
- Keep `results/d1-gpt41-all-benign-summary.json` open as a backup if the live
  provider or network is unavailable.
