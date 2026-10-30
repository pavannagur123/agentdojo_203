# Live Demo: Complete Steps from Scratch

This guide shows how to:

1. download and install the project;
2. provide the OpenRouter API key without creating an `.env` file;
3. run an existing AgentDojo task with a real PASS/FAIL evaluation; and
4. enter a completely new prompt during the presentation.

The reference configuration uses `openai/gpt-4.1` for the acting agent,
Planner LLM, and LLM Reviewer. The tools use synthetic AgentDojo data, not
real email, banking, Slack, travel, or calendar accounts.

## Part 1: Download and install the project

Open VS Code and select **Terminal > New Terminal**. Run these commands one at
a time:

```bash
git clone https://github.com/pavannagur123/agentdojo_203.git
cd agentdojo_203
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e .
```

You only need to clone and install the project once.

If the repository already exists on the computer, use:

```bash
cd agentdojo_203
git pull origin main
source .venv/bin/activate
```

## Part 2: Add the OpenRouter key in the terminal

The following method does not create an `.env` file and does not display the
key while it is pasted:

```bash
export OPENAI_COMPATIBLE_BASE_URL="https://openrouter.ai/api/v1"
read -s "OPENAI_COMPATIBLE_API_KEY?Paste your OpenRouter API key: "
echo
export OPENAI_COMPATIBLE_API_KEY
```

Paste the key when the terminal asks for it, then press **Enter**. Nothing will
appear while pasting; this is intentional.

The key remains available only in the current terminal. Repeat this section
after closing the terminal or opening a new one. Never place the key directly
inside a command, screenshot, slide, committed file, or chat message.

## Part 3: See the existing official inputs

List the official Workspace tasks and their exact prompts:

```bash
python -m agentdojo.scripts.live_demo list-tasks --suite workspace
```

The available suites are:

- `workspace` — email, contacts, and calendar tools;
- `banking` — simulated banking tools;
- `slack` — simulated messages and channels; and
- `travel` — simulated flights, hotels, and travel tools.

Change `workspace` to another suite name to see that suite's tasks:

```bash
python -m agentdojo.scripts.live_demo list-tasks --suite banking
```

## Part 4: Run an existing scored task

The recommended presentation task is:

```bash
python -m agentdojo.scripts.live_demo task \
  --suite workspace \
  --task user_task_18
```

The terminal first shows the exact evaluation input and asks:

```text
Run this paid OpenRouter demo now? [Y/n]
```

Press **Enter** or type `y` and press **Enter**.

The output shows:

- the acting-agent, Planner LLM, and LLM Reviewer models;
- the official input;
- PASS or FAIL against AgentDojo's ground truth;
- the acting agent's final response;
- every proposed tool call;
- its risk level;
- whether the policy approved or escalated it;
- the LLM Reviewer's final decision and explanation; and
- the full trace-file location.

`workspace/user_task_18` is useful for the presentation because read-only calls
are automatically approved, while the calendar write is escalated to the LLM
Reviewer.

To run a different existing task, replace the task ID:

```bash
python -m agentdojo.scripts.live_demo task \
  --suite workspace \
  --task user_task_6
```

Use only IDs shown by the `list-tasks` command for the selected suite.

## Part 5: Run a completely new input

Start interactive mode:

```bash
python -m agentdojo.scripts.live_demo prompt --suite workspace
```

The terminal displays:

```text
Enter the professor's input:
```

Type or paste the new request and press **Enter**. For example:

```text
Find the email about the hiking trip and tell me the proposed location.
```

The new input is passed through the same Planner LLM, acting agent, BASIL gate,
and LLM Reviewer used by the scored run.

You can also supply the new input directly in the command:

```bash
python -m agentdojo.scripts.live_demo prompt \
  --suite workspace \
  --input "Find the email about the hiking trip and tell me the proposed location."
```

Use the suite that contains the tools needed for the request. For example:

```bash
python -m agentdojo.scripts.live_demo prompt --suite banking
```

Important: a completely new prompt is reported as **not scored**. It still
shows the tool calls and approval decisions, but it cannot honestly show PASS
or FAIL because no ground-truth evaluator has been written for that new input.
This is expected behavior, not an error.

## Part 6: Where the live results are stored

Scored and custom demo records are saved locally under:

```text
runs/live-demo/
```

The `runs/` folder is ignored by Git, so large traces and local run data are not
committed. The terminal prints the exact JSON path after every run.

The committed full-run reference summary is available at:

```text
results/d1-gpt41-all-benign-summary.json
```

It records the verified full benign result of 68/97 tasks (70.10%).

## Part 7: Recommended presentation sequence

Before presenting:

1. Connect to a reliable network.
2. Confirm that the OpenRouter account has sufficient balance.
3. Open the repository in VS Code.
4. Activate the virtual environment.
5. Add the API key using the terminal commands in Part 2.
6. Run `workspace/user_task_18` once to confirm that everything works.
7. Clear the terminal before beginning the presentation if desired.

During the presentation:

1. Show the task using `list-tasks`.
2. Run `workspace/user_task_18`.
3. Point out the automatic read-only approvals.
4. Point out the calendar-write escalation.
5. Read the GPT-4.1 LLM Reviewer's explanation.
6. Show the PASS result and trace location.
7. Use `prompt` mode only if a new input is requested.

## Part 8: Common problems

### `No module named agentdojo`

Activate the environment and install the project:

```bash
source .venv/bin/activate
python -m pip install -e .
```

### Missing OpenRouter configuration

Repeat Part 2 in the same terminal used to run the demo.

### Authentication error or HTTP 401

The API key is missing, invalid, expired, or was pasted incorrectly. Repeat
Part 2 with a valid key.

### Insufficient credits or provider error

Check the OpenRouter account balance and model availability. The live run needs
internet access and makes paid model calls.

### The custom prompt says `not scored`

This is correct. Only registered AgentDojo tasks have programmed ground-truth
checks. Use the `task` command when the presentation requires PASS/FAIL.

### A date looks old

AgentDojo uses fixed synthetic benchmark data. A date returned by a tool belongs
to that simulated environment and is not necessarily today's real-world date.
