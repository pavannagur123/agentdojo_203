"""Run the reproducible PE6203 policy, budget, suite, and attack matrix."""

import json
from dataclasses import asdict, dataclass
from pathlib import Path

import click
from dotenv import load_dotenv

from agentdojo.approval.factory import APPROVAL_POLICIES, ApprovalPolicyName
from agentdojo.models import ModelsEnum
from agentdojo.scripts.basil_report import write_report_artifacts
from agentdojo.scripts.benchmark import benchmark_suite
from agentdojo.task_suite.load_suites import get_suite, get_suites


@dataclass(frozen=True)
class ExperimentSpec:
    policy: ApprovalPolicyName
    budget: int
    attack: str | None


def build_experiment_specs(
    policies: tuple[ApprovalPolicyName, ...],
    budgets: tuple[int, ...],
    attacks: tuple[str, ...],
) -> tuple[ExperimentSpec, ...]:
    """Build a de-duplicated matrix; full-approve is budget-independent."""

    normalized_attacks = tuple(None if attack.lower() == "none" else attack for attack in attacks)
    specs = []
    for policy in policies:
        policy_budgets = (0,) if policy == "full-approve" else budgets
        for budget in policy_budgets:
            for attack in normalized_attacks:
                specs.append(ExperimentSpec(policy=policy, budget=budget, attack=attack))
    return tuple(specs)


@click.command()
@click.option("--model", type=click.Choice([value for value in ModelsEnum]), default="openai-compatible")
@click.option("--model-id", type=str, required=True, help="Agent model id for the OpenAI-compatible provider.")
@click.option("--reviewer-model", type=str, required=True, help="LLM-simulated human reviewer model id.")
@click.option("--planner-model", type=str, default=None, help="Optional authorization-planner model id.")
@click.option("--benchmark-version", type=str, default="v1.2.2", show_default=True)
@click.option("--suite", "suites", type=str, multiple=True, help="Suite to run; repeat for multiple suites.")
@click.option(
    "--policy",
    "policies",
    type=click.Choice(APPROVAL_POLICIES),
    multiple=True,
    help="Policy to run; defaults to all three policies.",
)
@click.option(
    "--budget",
    "budgets",
    type=click.IntRange(min=0),
    multiple=True,
    default=(0, 1, 2, 3),
    show_default=True,
    help="Escalation budget; repeat to define the TCR@k range.",
)
@click.option(
    "--attack",
    "attacks",
    type=str,
    multiple=True,
    default=("none",),
    show_default=True,
    help="Attack name or 'none'; repeat to compare attack conditions.",
)
@click.option("--output-dir", type=Path, default=Path("runs/basil-matrix"), show_default=True)
@click.option("--force-rerun", is_flag=True, help="Re-run traces that already exist.")
@click.option("--dry-run", is_flag=True, help="Write the manifest without making model calls.")
def main(
    model: ModelsEnum,
    model_id: str,
    reviewer_model: str,
    planner_model: str | None,
    benchmark_version: str,
    suites: tuple[str, ...],
    policies: tuple[ApprovalPolicyName, ...],
    budgets: tuple[int, ...],
    attacks: tuple[str, ...],
    output_dir: Path,
    force_rerun: bool,
    dry_run: bool,
) -> None:
    load_dotenv(".env")
    selected_suites = suites or tuple(get_suites(benchmark_version).keys())
    selected_policies = policies or APPROVAL_POLICIES
    specs = build_experiment_specs(selected_policies, budgets, attacks)
    manifest = {
        "benchmark_version": benchmark_version,
        "model": str(model),
        "model_id": model_id,
        "reviewer_model": reviewer_model,
        "planner_model": planner_model,
        "suites": selected_suites,
        "specs": [asdict(spec) for spec in specs],
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "experiment-manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True))
    if dry_run:
        click.echo(f"Planned {len(specs)} configurations across {len(selected_suites)} suites.")
        return

    for spec in specs:
        click.echo(
            f"Running policy={spec.policy}, k={spec.budget}, attack={spec.attack or 'none'} "
            f"across {len(selected_suites)} suites"
        )
        for suite_name in selected_suites:
            benchmark_suite(
                get_suite(benchmark_version, suite_name),
                model,
                output_dir,
                force_rerun,
                benchmark_version,
                model_id=model_id,
                attack=spec.attack,
                approval_policy=spec.policy,
                approval_budget=spec.budget,
                approval_reviewer_model=reviewer_model,
                approval_planner_model=planner_model,
            )

    report = write_report_artifacts(
        output_dir,
        output_dir / "report.json",
        output_dir / "summary.csv",
        output_dir / "tcr-at-k.csv",
        output_dir / "tcr-at-k.svg",
        output_dir / "escalation-value.csv",
    )
    click.echo(f"Completed {len(specs)} configurations; aggregated {report['trace_count']} traces.")


if __name__ == "__main__":
    main()
