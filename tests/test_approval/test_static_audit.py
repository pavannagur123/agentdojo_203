from agentdojo.scripts.basil_static_audit import run_static_audit


def test_static_audit_covers_all_suites_without_auto_denying_legitimate_calls() -> None:
    report = run_static_audit("v1.2.2")

    assert set(report["suites"]) == {"workspace", "travel", "banking", "slack"}
    for suite in report["suites"].values():
        assert suite["denied_legitimate_calls"] == []
        assert 0.0 <= suite["malicious_side_effect_proxy_auto_approve_rate"] <= 1.0
