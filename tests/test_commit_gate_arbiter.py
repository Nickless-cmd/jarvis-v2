"""Tests for governed commit-gate arbitrage (commit_gate_arbiter)."""
from __future__ import annotations

from core.services import central_core, central_switches, commit_gate_arbiter
from core.services.gate_kernel import Decision, GateClass, Verdict


class _FakeCentral:
    """Stub der returnerer forud-bestemte verdicts pr. nerve og sluger observe()."""

    def __init__(self, verdicts: dict) -> None:
        self._v = verdicts

    def decide(self, nerve, ctx, fn, **kw):  # noqa: ANN001
        return self._v.get(nerve)

    def observe(self, *a, **k):  # noqa: ANN002, ANN003
        return None


def _evaluate():
    return commit_gate_arbiter.evaluate_commit_gates(
        name="write_file", arguments={}, user_message="", session_id="s", run_id="r",
    )


def test_veto_red_blocks_when_enforced(monkeypatch) -> None:
    central_switches.set_enabled("gate_enforce", "veto", True)
    fake = _FakeCentral({
        "veto": Verdict("veto", Decision.RED, "nej", evidence={"reason": "nej"}),
        "decision_gate": Verdict("decision_gate", Decision.GREEN),
    })
    monkeypatch.setattr(central_core, "central", lambda: fake)
    out = _evaluate()
    assert out.blocked is True
    assert out.gate_type == "veto_gate"
    assert out.reason == "nej"


def test_veto_red_suppressed_when_disabled(monkeypatch) -> None:
    """Kill-switchet veto → RED håndhæves IKKE (observe-only): tool må køre."""
    central_switches.set_enabled("gate_enforce", "veto", False)
    try:
        fake = _FakeCentral({
            "veto": Verdict("veto", Decision.RED, "nej", evidence={"reason": "nej"}),
            "decision_gate": Verdict("decision_gate", Decision.GREEN),
        })
        monkeypatch.setattr(central_core, "central", lambda: fake)
        out = _evaluate()
        assert out.blocked is False
    finally:
        central_switches.set_enabled("gate_enforce", "veto", True)


def test_decision_gate_red_blocks_when_enforced(monkeypatch) -> None:
    central_switches.set_enabled("gate_enforce", "decision_gate", True)
    fake = _FakeCentral({
        "veto": Verdict("veto", Decision.GREEN),
        "decision_gate": Verdict("decision_gate", Decision.RED, "konflikt"),
    })
    monkeypatch.setattr(central_core, "central", lambda: fake)
    out = _evaluate()
    assert out.blocked is True
    assert out.gate_type == "decision_gate"


def test_decision_gate_red_suppressed_when_disabled(monkeypatch) -> None:
    central_switches.set_enabled("gate_enforce", "decision_gate", False)
    try:
        fake = _FakeCentral({
            "veto": Verdict("veto", Decision.GREEN),
            "decision_gate": Verdict("decision_gate", Decision.RED, "konflikt"),
        })
        monkeypatch.setattr(central_core, "central", lambda: fake)
        out = _evaluate()
        assert out.blocked is False
    finally:
        central_switches.set_enabled("gate_enforce", "decision_gate", True)


def test_decision_gate_yellow_soft_warns(monkeypatch) -> None:
    """YELLOW blokerer aldrig — surfaces som blød advarsel (uafhængigt af enforce-flag)."""
    fake = _FakeCentral({
        "veto": Verdict("veto", Decision.GREEN),
        "decision_gate": Verdict("decision_gate", Decision.YELLOW, "blød tension"),
    })
    monkeypatch.setattr(central_core, "central", lambda: fake)
    out = _evaluate()
    assert out.blocked is False
    assert out.soft_warn == "blød tension"


def test_all_green_allows(monkeypatch) -> None:
    fake = _FakeCentral({
        "veto": Verdict("veto", Decision.GREEN),
        "decision_gate": Verdict("decision_gate", Decision.GREEN),
    })
    monkeypatch.setattr(central_core, "central", lambda: fake)
    out = _evaluate()
    assert out.blocked is False
    assert out.soft_warn is None


def test_gate_error_fails_open(monkeypatch) -> None:
    """Central-fejl → allow (fail-open, paritet med gammelt inline-except)."""
    class _Boom:
        def decide(self, *a, **k):  # noqa: ANN002, ANN003
            raise RuntimeError("central nede")
        def observe(self, *a, **k):  # noqa: ANN002, ANN003
            return None
    monkeypatch.setattr(central_core, "central", lambda: _Boom())
    out = _evaluate()
    assert out.blocked is False
