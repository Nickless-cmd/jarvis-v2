from core.services import reasoning_interceptor as ri
from core.services.gate_kernel import Decision, Verdict


def test_empty_reasoning_is_green_noop():
    out = ri.intercept_round(run_id="r", round_num=1, reasoning_text="",
                             tool_calls_this_run=[], ctx={})
    assert out.grade is Decision.GREEN and out.correction is None


def test_no_risk_class_is_green_noop():
    out = ri.intercept_round(run_id="r", round_num=1,
                             reasoning_text="Just pondering the question.",
                             tool_calls_this_run=[], ctx={})
    assert out.grade is Decision.GREEN and out.correction is None


def test_shadow_default_never_returns_correction(monkeypatch):
    monkeypatch.setattr(ri, "_run_detectors",
                        lambda ctx: Verdict("fact_gate", Decision.RED, "unbacked", action="block"))
    monkeypatch.setattr(ri, "_is_active", lambda grade: False)  # shadow
    out = ri.intercept_round(run_id="r", round_num=1,
                             reasoning_text="The table has 4231 rows.",
                             tool_calls_this_run=[], ctx={})
    assert out.shadow is True and out.correction is None
    assert out.grade is Decision.RED  # verdict recorded even in shadow


def test_fail_open_on_detector_exception(monkeypatch):
    monkeypatch.setattr(ri, "_run_detectors",
                        lambda ctx: (_ for _ in ()).throw(RuntimeError("boom")))
    out = ri.intercept_round(run_id="r", round_num=1,
                             reasoning_text="The table has 4231 rows.",
                             tool_calls_this_run=[], ctx={})
    assert out.grade is Decision.GREEN  # never breaks the run


def test_observe_is_metadata_only_and_self_safe(monkeypatch):
    seen = {}
    def _fake_record_private(cluster, nerve, *, value=0.0, meta=None):
        seen.update({"cluster": cluster, "nerve": nerve, "meta": meta or {}})
    monkeypatch.setattr("core.services.central_private_observe.record_private", _fake_record_private)
    ri._observe(ri.InterceptOutcome(grade=ri.Decision.YELLOW, triggers=["fact_gate"],
                                    shadow=True, latency_ms=12), run_id="r", round_num=2)
    assert seen["nerve"] == "reasoning_interceptor"
    assert "reasoning_text" not in seen["meta"] and seen["meta"].get("grade") == "yellow"


def test_run_detectors_aggregates_worst_via_central(monkeypatch):
    from core.services.gate_kernel import Verdict, Decision as _D
    monkeypatch.setattr("core.services.reasoning_detectors.fact_gate_on_reasoning",
                        lambda t, c: Verdict("fact_gate", _D.YELLOW, "claim", action="warn"))
    monkeypatch.setattr("core.services.reasoning_detectors.standing_orders_on_reasoning",
                        lambda t, c: None)
    out = ri.intercept_round(run_id="r", round_num=1, reasoning_text="The DB has 4231 rows.",
                             tool_calls_this_run=[], ctx={})
    assert out.grade is _D.YELLOW and "fact_gate" in out.triggers


def test_is_active_default_off_shadow():
    from core.services.gate_kernel import Decision as _D
    assert ri._is_active(_D.YELLOW) is False
    assert ri._is_active(_D.RED) is False
    assert ri._is_active(_D.GREEN) is False


def test_is_active_reads_flipped_flag():
    from core.services.gate_kernel import Decision as _D
    from core.services import shared_cache
    shared_cache.set("flag:central.switch.gate_enforce.reasoning_interceptor_yellow",
                     {"enabled": True}, ttl_seconds=60)
    try:
        assert ri._is_active(_D.YELLOW) is True
        assert ri._is_active(_D.RED) is False
    finally:
        shared_cache.set("flag:central.switch.gate_enforce.reasoning_interceptor_yellow",
                         {"enabled": False}, ttl_seconds=60)


def test_should_hold_tool_call_only_active_red():
    from core.services.gate_kernel import Decision as _D
    assert ri.should_hold_tool_call(ri.InterceptOutcome(grade=_D.RED, shadow=False)) is True
    assert ri.should_hold_tool_call(ri.InterceptOutcome(grade=_D.RED, shadow=True)) is False
    assert ri.should_hold_tool_call(ri.InterceptOutcome(grade=_D.YELLOW, shadow=False)) is False
