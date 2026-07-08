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
