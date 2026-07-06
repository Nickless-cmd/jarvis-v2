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
