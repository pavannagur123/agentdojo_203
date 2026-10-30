"""Presentation-friendly live runner for the PE6203 LLM approval pipeline."""

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import click
from dotenv import load_dotenv
from rich.console import Console
from rich.table import Table

from agentdojo.agent_pipeline import AgentPipeline, PipelineConfig
from agentdojo.functions_runtime import FunctionsRuntime
from agentdojo.models import ModelsEnum
from agentdojo.scripts.benchmark import benchmark_suite
from agentdojo.task_suite.load_suites import get_suite, get_suites
from agentdojo.types import ChatMessage, get_text_content_as_str

REFERENCE_MODEL = "openai/gpt-4.1"
BENCHMARK_VERSION = "v1.2.2"
DEFAULT_LOGDIR = Path("runs/live-demo")
console = Console()


def _require_openrouter_config() -> None:
    load_dotenv(".env")
    missing = [
        name
        for name in ("OPENAI_COMPATIBLE_BASE_URL", "OPENAI_COMPATIBLE_API_KEY")
        if not os.getenv(name)
    ]
    if missing:
        names = ", ".join(missing)
        raise click.ClickException(
            f"Missing {names}. Copy .env.example to .env and add the OpenRouter API key before the demo."
        )


def _last_response(messages: list[dict[str, Any]] | list[ChatMessage]) -> str:
    for message in reversed(messages):
        if message.get("role") != "assistant" or not message.get("content"):
            continue
        content = message["content"]
        if isinstance(content, str):
            return content
        if content is not None:
            return get_text_content_as_str(content)
    return "(No final text response was produced.)"


def _show_configuration(agent_model: str, planner_model: str, reviewer_model: str, budget: int) -> None:
    table = Table(title="Live LLM approval configuration", show_header=False)
    table.add_column("Role", style="cyan")
    table.add_column("Model / value", style="white")
    table.add_row("Acting agent", agent_model)
    table.add_row("Planner LLM", planner_model)
    table.add_row("LLM Reviewer", reviewer_model)
    table.add_row("Policy", "basil")
    table.add_row("Review budget", str(budget))
    console.print(table)


def _show_decisions(basil: dict[str, Any]) -> None:
    decisions = basil.get("decisions") or []
    table = Table(title="Tool-call approval decisions")
    table.add_column("#", justify="right")
    table.add_column("Tool")
    table.add_column("Risk")
    table.add_column("Policy")
    table.add_column("Final")
    table.add_column("LLM Reviewer reason")
    for decision in decisions:
        reviewer_reason = decision.get("reviewer_reason") or "—"
        table.add_row(
            str(decision.get("sequence", "")),
            str(decision.get("function", "")),
            str(decision.get("risk", "")),
            str(decision.get("policy_decision", "")),
            str(decision.get("final_decision", "")),
            reviewer_reason,
        )
    if decisions:
        console.print(table)
    else:
        console.print("[yellow]No tool calls were proposed, so the LLM Reviewer was not needed.[/yellow]")

    actual_reviews = sum(1 for decision in decisions if decision.get("reviewer_reason"))
    console.print(
        f"Escalations used: [bold]{basil.get('escalations_used', 0)}"
        f"/{basil.get('escalation_budget', 0)}[/bold] | Actual LLM Reviewer calls: [bold]{actual_reviews}[/bold]"
    )


def _write_custom_snapshot(
    logdir: Path,
    suite_name: str,
    prompt: str,
    response: str,
    extra_args: dict[str, Any],
    models: dict[str, str],
) -> Path:
    logdir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = logdir / f"custom-{suite_name}-{timestamp}.json"
    snapshot = {
        "timestamp": timestamp,
        "mode": "custom-prompt-not-scored",
        "suite": suite_name,
        "prompt": prompt,
        "response": response,
        "models": models,
        "agent_usage": extra_args.get("agent_usage", {}),
        "basil": extra_args.get("basil", {}),
    }
    path.write_text(json.dumps(snapshot, indent=2, default=str))
    return path


@click.group()
def main() -> None:
    """Run a scored benchmark task or an unscored custom prompt live."""


@main.command("list-tasks")
@click.option("--suite", "suite_name", default="workspace", show_default=True)
def list_tasks(suite_name: str) -> None:
    """List official tasks and their exact prompts."""

    if suite_name not in get_suites(BENCHMARK_VERSION):
        raise click.ClickException(f"Unknown suite '{suite_name}'. Choose banking, slack, travel, or workspace.")
    suite = get_suite(BENCHMARK_VERSION, suite_name)
    table = Table(title=f"{suite_name.title()} benchmark tasks")
    table.add_column("Task ID", style="cyan", no_wrap=True)
    table.add_column("Prompt")
    for task_id, task in suite.user_tasks.items():
        table.add_row(task_id, task.PROMPT)
    console.print(table)


@main.command("task")
@click.option("--suite", "suite_name", default="workspace", show_default=True)
@click.option("--task", "task_id", default="user_task_18", show_default=True)
@click.option("--agent-model", default=REFERENCE_MODEL, show_default=True)
@click.option("--planner-model", default=REFERENCE_MODEL, show_default=True)
@click.option("--reviewer-model", default=REFERENCE_MODEL, show_default=True)
@click.option("--budget", type=click.IntRange(min=0), default=2, show_default=True)
@click.option("--logdir", type=click.Path(path_type=Path), default=DEFAULT_LOGDIR, show_default=True)
@click.option("--yes", is_flag=True, help="Skip the confirmation prompt.")
def run_task(
    suite_name: str,
    task_id: str,
    agent_model: str,
    planner_model: str,
    reviewer_model: str,
    budget: int,
    logdir: Path,
    yes: bool,
) -> None:
    """Run one official task and show its scored result and approval ledger."""

    _require_openrouter_config()
    if suite_name not in get_suites(BENCHMARK_VERSION):
        raise click.ClickException(f"Unknown suite '{suite_name}'. Choose banking, slack, travel, or workspace.")
    suite = get_suite(BENCHMARK_VERSION, suite_name)
    if task_id not in suite.user_tasks:
        raise click.ClickException(f"Unknown task '{task_id}'. Run the list-tasks command to see valid IDs.")
    task = suite.user_tasks[task_id]

    _show_configuration(agent_model, planner_model, reviewer_model, budget)
    console.print(f"[dim]Sandbox: synthetic AgentDojo {suite_name} data (not live personal accounts).[/dim]")
    console.print("\n[bold]Official evaluation input[/bold]")
    console.print(task.PROMPT)
    if not yes and not click.confirm("Run this paid OpenRouter demo now?", default=True):
        raise click.Abort()

    results = benchmark_suite(
        suite,
        ModelsEnum("openai-compatible"),
        logdir,
        force_rerun=True,
        benchmark_version=BENCHMARK_VERSION,
        user_tasks=(task_id,),
        model_id=agent_model,
        approval_policy="basil",
        approval_budget=budget,
        approval_reviewer_model=reviewer_model,
        approval_planner_model=planner_model,
    )
    passed = all(results["utility_results"].values())
    trace_candidates = [path for path in logdir.rglob("none.json") if task_id in path.parts]
    if not trace_candidates:
        raise click.ClickException("The task finished, but its trace file could not be located.")
    trace_path = max(trace_candidates, key=lambda path: path.stat().st_mtime)
    trace = json.loads(trace_path.read_text())

    console.rule("Scored result")
    console.print("[bold green]PASS[/bold green]" if passed else "[bold red]FAIL[/bold red]")
    console.print(f"\n[bold]Agent response[/bold]\n{_last_response(trace.get('messages', []))}")
    _show_decisions(trace.get("basil") or {})
    usage = trace.get("agent_usage") or {}
    console.print(f"Agent provider-reported cost: [bold]USD {usage.get('cost_usd', 0):.6f}[/bold]")
    console.print(f"Full trace: [cyan]{trace_path.resolve()}[/cyan]")


@main.command("prompt")
@click.option("--suite", "suite_name", default="workspace", show_default=True)
@click.option("--input", "prompt_text", default=None, help="Prompt text; omit it to type interactively.")
@click.option("--agent-model", default=REFERENCE_MODEL, show_default=True)
@click.option("--planner-model", default=REFERENCE_MODEL, show_default=True)
@click.option("--reviewer-model", default=REFERENCE_MODEL, show_default=True)
@click.option("--budget", type=click.IntRange(min=0), default=2, show_default=True)
@click.option("--logdir", type=click.Path(path_type=Path), default=DEFAULT_LOGDIR, show_default=True)
def run_prompt(
    suite_name: str,
    prompt_text: str | None,
    agent_model: str,
    planner_model: str,
    reviewer_model: str,
    budget: int,
    logdir: Path,
) -> None:
    """Run arbitrary input through the real tools and approval pipeline."""

    _require_openrouter_config()
    if suite_name not in get_suites(BENCHMARK_VERSION):
        raise click.ClickException(f"Unknown suite '{suite_name}'. Choose banking, slack, travel, or workspace.")
    resolved_prompt: str = prompt_text or click.prompt("Enter the professor's input")
    suite = get_suite(BENCHMARK_VERSION, suite_name)
    pipeline = AgentPipeline.from_config(
        PipelineConfig(
            llm="openai-compatible",
            model_id=agent_model,
            defense=None,
            system_message_name=None,
            system_message=None,
            approval_policy="basil",
            approval_budget=budget,
            approval_reviewer_model=reviewer_model,
            approval_planner_model=planner_model,
        )
    )
    runtime = FunctionsRuntime(suite.tools)
    environment = suite.load_and_inject_default_environment({})

    _show_configuration(agent_model, planner_model, reviewer_model, budget)
    console.print(f"[dim]Sandbox: synthetic AgentDojo {suite_name} data (not live personal accounts).[/dim]")
    console.print(f"\n[bold]Custom input[/bold]\n{resolved_prompt}")
    _, _, _, messages, extra_args = pipeline.query(resolved_prompt, runtime, environment)
    response = _last_response(list(messages))
    models = {"agent": agent_model, "planner": planner_model, "reviewer": reviewer_model}
    snapshot_path = _write_custom_snapshot(logdir, suite_name, resolved_prompt, response, extra_args, models)

    console.rule("Live result (not scored)")
    console.print(response)
    _show_decisions(extra_args.get("basil") or {})
    usage = extra_args.get("agent_usage") or {}
    console.print(f"Agent provider-reported cost: [bold]USD {usage.get('cost_usd', 0):.6f}[/bold]")
    console.print("[yellow]No PASS/FAIL is shown because custom input has no benchmark ground truth.[/yellow]")
    console.print(f"Saved demo record: [cyan]{snapshot_path.resolve()}[/cyan]")


if __name__ == "__main__":
    main()
