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


class _RecordingCentral:
    """Fake der noterer HVILKE nerver der routes gennem central().decide."""

    def __init__(self, verdicts: dict, called: list) -> None:
        self._v = verdicts
        self._called = called

    def decide(self, nerve, ctx, fn, **kw):  # noqa: ANN001
        self._called.append(nerve)
        return self._v.get(nerve, Verdict(nerve, Decision.GREEN))

    def observe(self, *a, **k):  # noqa: ANN002, ANN003
        return None


def test_decentralized_veto_resolves_locally_skipping_central(monkeypatch) -> None:
    """En gyldig decentralize:veto-nøgle + lokalt GRØNT → veto resolves LOKALT (springer Centralens
    round-trip over); decision_gate routes stadig gennem Centralen."""
    from core.services import gate_commit
    monkeypatch.setattr("core.services.central_keymaker.is_decentralized", lambda n: n == "veto")
    monkeypatch.setattr(gate_commit, "veto_gate",
                        lambda ctx: Verdict("veto", Decision.GREEN, "tilladt"))
    called: list = []
    monkeypatch.setattr(central_core, "central",
                        lambda: _RecordingCentral({}, called))
    out = _evaluate()
    assert out.blocked is False
    assert "veto" not in called          # veto løst lokalt — central-skat sprunget over
    assert "decision_gate" in called     # decision_gate stadig gennem Centralen


def test_decentralized_veto_escalates_on_nongreen(monkeypatch) -> None:
    """Decentraliseret, men lokalt IKKE-grønt (RED) → eskalér til fuld central-arbitrage; RED +
    enforce → blokér (selv-tilbageholdenhed bevaret trods decentralisering)."""
    from core.services import gate_commit
    central_switches.set_enabled("gate_enforce", "veto", True)
    monkeypatch.setattr("core.services.central_keymaker.is_decentralized", lambda n: n == "veto")
    monkeypatch.setattr(gate_commit, "veto_gate",
                        lambda ctx: Verdict("veto", Decision.RED, "nej", evidence={"reason": "nej"}))
    called: list = []
    monkeypatch.setattr(central_core, "central", lambda: _RecordingCentral(
        {"veto": Verdict("veto", Decision.RED, "nej", evidence={"reason": "nej"})}, called))
    out = _evaluate()
    assert "veto" in called               # eskaleret til Centralen fordi lokalt var ikke-grønt
    assert out.blocked is True            # central RED + enforce → blokeret
