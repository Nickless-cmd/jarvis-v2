"""Track 2 shadow — 5 sovende post_output-gates via central().decide.

HÅRDT INVARIANT: SHADOW = record verdict, ALDRIG enforce. run_post_output_shadow
returnerer None, kaster aldrig, og bruges ikke til at blokere turen.
"""
from __future__ import annotations

from unittest import mock

from core.services.gate_kernel import Decision, GateClass, Verdict
import core.services.gate_shadow as gs


# De 5 forventede (nerve, cluster) — nerve-navn = Verdict.gate fra hver fn.
EXPECTED = [
    ("decision_gate", "commit"),
    ("loop_control", "loop"),
    ("verification", "proactivity"),
    ("self_review", "review"),
    ("fact_gate", "truth"),  # nerve = Verdict.gate fra fact_gate_adapter
]


def _ctx() -> dict:
    return {
        "text": "hej",
        "tool_names": ["a"],
        "tools_used": ["a"],
        "run_id": "r1",
        "session_id": "s1",
    }


def test_calls_decide_5_times_with_clusters():
    """run_post_output_shadow kalder central().decide 5× — én pr. gate, korrekt cluster."""
    fake_central = mock.MagicMock()
    fake_central.decide.return_value = Verdict("x", Decision.GREEN, "ok")
    with mock.patch.object(gs, "central", return_value=fake_central), \
            mock.patch.object(gs, "_shadow_enabled", return_value=True):
        result = gs.run_post_output_shadow(_ctx())

    assert result is None
    assert fake_central.decide.call_count == 6  # 5 cognitive + privacy (SECURITY)

    seen_clusters = []
    seen_nerves = []
    for call in fake_central.decide.call_args_list:
        nerve = call.args[0]
        cluster = call.kwargs.get("cluster")
        klass = call.kwargs.get("klass")
        seen_nerves.append(nerve)
        seen_clusters.append(cluster)
        assert klass is (GateClass.SECURITY if nerve == "cross_user_share" else GateClass.COGNITIVE)
    assert seen_clusters == [c for (_n, c) in gs.POST_OUTPUT_GATES_CLUSTERS()]
    assert seen_nerves == [n for (n, _c) in gs.POST_OUTPUT_GATES_CLUSTERS()]


def test_one_gate_import_failure_does_not_stop_others():
    """Én gate der kaster i decide → de øvrige 4 kaldes stadig; ingen exception propagerer."""
    fake_central = mock.MagicMock()

    calls = {"n": 0}

    def _decide(nerve, ctx, fn, **kw):
        calls["n"] += 1
        if calls["n"] == 2:
            raise RuntimeError("gate exploded")
        return Verdict("x", Decision.GREEN, "ok")

    fake_central.decide.side_effect = _decide
    with mock.patch.object(gs, "central", return_value=fake_central), \
            mock.patch.object(gs, "_shadow_enabled", return_value=True):
        result = gs.run_post_output_shadow(_ctx())

    assert result is None
    # alle 5 forsøgt trods én der kastede
    assert calls["n"] == 6  # 5 cognitive + privacy


def test_flag_off_skips_all():
    """Flag gate_kernel.shadow=False → 0 decide-kald."""
    fake_central = mock.MagicMock()
    with mock.patch.object(gs, "central", return_value=fake_central), \
            mock.patch.object(gs, "_shadow_enabled", return_value=False):
        result = gs.run_post_output_shadow(_ctx())
    assert result is None
    assert fake_central.decide.call_count == 0


def test_self_safe_central_raises():
    """central() der kaster → ingen exception propagerer, returnerer None."""
    with mock.patch.object(gs, "central", side_effect=RuntimeError("no central")), \
            mock.patch.object(gs, "_shadow_enabled", return_value=True):
        result = gs.run_post_output_shadow(_ctx())
    assert result is None


def test_self_safe_garbage_ctx():
    """Skør ctx (None) → ingen exception."""
    fake_central = mock.MagicMock()
    fake_central.decide.return_value = Verdict("x", Decision.GREEN, "ok")
    with mock.patch.object(gs, "central", return_value=fake_central), \
            mock.patch.object(gs, "_shadow_enabled", return_value=True):
        result = gs.run_post_output_shadow(None)  # type: ignore[arg-type]
    assert result is None


def test_flag_read_self_safe():
    """_shadow_enabled fail-open til True hvis switch-læsning kaster (default ON)."""
    with mock.patch("core.services.central_switches.is_enabled",
                    side_effect=RuntimeError("cache down")):
        assert gs._shadow_enabled() is True


def test_enforced_gate_records_incident_on_nongreen():
    """ENFORCE-graduering (6. jul): en enforced gates ikke-grønne verdict → central-incident
    (synligt). Non-destruktivt. loop_control er IKKE enforced → intet incident."""
    from core.services.gate_kernel import Decision, GateClass, Verdict
    import core.services.gate_shadow as gs

    recorded = []
    fake_central = mock.MagicMock()
    # decision_gate (enforced) returnerer YELLOW; loop_control (shadow) returnerer YELLOW
    def _decide(nerve, ctx, fn, *, cluster, klass):
        return Verdict(nerve, Decision.YELLOW, f"{nerve}-tvivl", klass=klass)
    fake_central.decide.side_effect = _decide

    with mock.patch.object(gs, "central", return_value=fake_central), \
            mock.patch.object(gs, "_shadow_enabled", return_value=True), \
            mock.patch("core.runtime.db_central_incidents.record_central_incident",
                       side_effect=lambda **k: recorded.append(k)):
        gs.run_post_output_shadow(_ctx())

    nerves = {r["nerve"] for r in recorded}
    # enforced gates m. non-green → incident
    assert "decision_gate" in nerves and "verification" in nerves and "self_review" in nerves
    # loop_control er shadow-only → ALDRIG et enforce-incident
    assert "loop_control" not in nerves
    # YELLOW blød-surface → severity info (degraderer IKKE Central-helbred)
    assert all(r["severity"] == "info" for r in recorded if r["nerve"] == "decision_gate")


def test_enforce_severity_by_grade():
    """Severitet efter GRAD: YELLOW blød-surface → info (normal governance, ingen unhealth);
    RED hård blok → error; SECURITY-RED → severe; GREEN → intet incident."""
    from core.services.gate_kernel import Decision, GateClass, Verdict
    import core.services.gate_shadow as gs
    rec: list = []
    with mock.patch("core.runtime.db_central_incidents.record_central_incident",
                    side_effect=lambda **k: rec.append(k)):
        gs._enforce_verdict("verification", "proactivity", GateClass.COGNITIVE,
                            Verdict("verification", Decision.YELLOW, "blød"))
        gs._enforce_verdict("decision_gate", "commit", GateClass.COGNITIVE,
                            Verdict("decision_gate", Decision.RED, "hård"))
        gs._enforce_verdict("cross_user_share", "privacy", GateClass.SECURITY,
                            Verdict("cross_user_share", Decision.RED, "sec"))
        gs._enforce_verdict("x", "y", GateClass.COGNITIVE,
                            Verdict("x", Decision.GREEN, "ok"))
    by_nerve = {r["nerve"]: r["severity"] for r in rec}
    assert by_nerve["verification"] == "info"
    assert by_nerve["decision_gate"] == "error"
    assert by_nerve["cross_user_share"] == "severe"
    assert "x" not in by_nerve


def test_enforced_set_excludes_loop_control():
    import core.services.gate_shadow as gs
    assert gs._is_enforced("cross_user_share") is True
    assert gs._is_enforced("decision_gate") is True
    assert gs._is_enforced("loop_control") is False  # bevidst i shadow
