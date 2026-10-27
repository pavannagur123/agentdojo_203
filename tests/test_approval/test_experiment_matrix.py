from agentdojo.scripts.basil_experiment import build_experiment_specs


def test_matrix_covers_baselines_budgets_and_attacks_without_duplicate_full_approve() -> None:
    specs = build_experiment_specs(
        ("full-approve", "full-escalate", "basil"),
        (0, 1, 2, 3),
        ("none", "important_instructions"),
    )

    assert len(specs) == 18
    assert sum(spec.policy == "full-approve" for spec in specs) == 2
    assert {spec.budget for spec in specs if spec.policy == "basil"} == {0, 1, 2, 3}
    assert {spec.attack for spec in specs} == {None, "important_instructions"}
