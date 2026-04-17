"""Smoke test for core.services.runtime_learning_signals.

Learning signal extraction should convert a blocked executive outcome into both
action-level and family-level feedback signals.
"""

from core.services import runtime_learning_signals


def test_extract_runtime_learning_signals_for_blocked_repo_action() -> None:
    outcome = {
        "outcome_id": "out-1",
        "action_id": "inspect_repo_context",
        "recorded_at": "2026-04-17T10:00:00+00:00",
        "result_status": "blocked",
        "result_summary": "Repo capability blocked after no change.",
        "payload": {"focus": "git repo status"},
        "result": {
            "details": {},
            "side_effects": ["repo-context-inspected", "workspace-capability-blocked"],
        },
    }

    signals = runtime_learning_signals.extract_runtime_learning_signals(outcome)
    signal_keys = {item["signal_key"] for item in signals}

    assert "action_blocked" in signal_keys
    assert "family_blocked" in signal_keys
    assert "repo_capability_blocked" in signal_keys
