"""Fase 6 Task 8 — unit tests for scripts/acceptance/migration_gate.py's pure
verdict logic (`evaluate`). No subprocess, no real suite runs — mirrors the
script's own `--self-test` mode as a committed pytest regression."""
from __future__ import annotations

from scripts.acceptance.migration_gate import evaluate

_ALL_GREEN = {
    "client_fault_injection": {"ok": True},
    "server_fault_injection": {"ok": True},
    "multi_user_scoping": {"ok": True},
    "security_floor": {"ok": True},
    "e2e_devtask": {"ok": True},
    "numeric_bar": {"silent_empty": 0, "hangs": 0, "orphan_400": 0, "n": 100},
}


def test_go_true_when_everything_green():
    v = evaluate(_ALL_GREEN)
    assert v["go"] is True
    assert v["failing_criteria"] == []


def test_go_false_when_silent_empty_nonzero():
    results = dict(_ALL_GREEN, numeric_bar={"silent_empty": 1, "hangs": 0, "orphan_400": 0, "n": 100})
    v = evaluate(results)
    assert v["go"] is False
    assert "1_numeric_bar_0_0_0_over_n100" in v["failing_criteria"]


def test_go_false_when_hangs_nonzero():
    results = dict(_ALL_GREEN, numeric_bar={"silent_empty": 0, "hangs": 1, "orphan_400": 0, "n": 100})
    assert evaluate(results)["go"] is False


def test_go_false_when_orphan_nonzero():
    results = dict(_ALL_GREEN, numeric_bar={"silent_empty": 0, "hangs": 0, "orphan_400": 1, "n": 100})
    assert evaluate(results)["go"] is False


def test_go_false_when_e2e_failed():
    results = dict(_ALL_GREEN, e2e_devtask={"ok": False})
    v = evaluate(results)
    assert v["go"] is False
    assert "2_e2e_devtask_passed" in v["failing_criteria"]


def test_go_false_when_security_floor_failed():
    results = dict(_ALL_GREEN, security_floor={"ok": False})
    v = evaluate(results)
    assert v["go"] is False
    assert "4_security_floor_active" in v["failing_criteria"]


def test_go_false_when_scoping_failed():
    results = dict(_ALL_GREEN, multi_user_scoping={"ok": False})
    v = evaluate(results)
    assert v["go"] is False
    assert "4_security_floor_active" in v["failing_criteria"]


def test_go_false_when_numeric_bar_missing():
    results = dict(_ALL_GREEN, numeric_bar={})
    assert evaluate(results)["go"] is False


def test_go_false_when_fault_injection_suite_itself_failed():
    results = dict(_ALL_GREEN, client_fault_injection={"ok": False})
    v = evaluate(results)
    assert v["go"] is False
    assert "1_fault_injection_harness_green" in v["failing_criteria"]


def test_verdict_always_has_a_timestamp_and_numeric_bar_echo():
    v = evaluate(_ALL_GREEN)
    assert v["timestamp"]
    assert v["numeric_bar"] == {"silent_empty": 0, "hangs": 0, "orphan_400": 0, "n": 100}
