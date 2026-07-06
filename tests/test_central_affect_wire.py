"""Tests for affekt-wiring i central_core.observe (BULLETPROOF self-safe).

Bevis: (1) observe farver trace-record'en med affect + affect_intensity;
(2) et flag-event bliver til uro; (3) hvis classifieren KASTER, brækker observe
IKKE — trace-record'en gemmes stadig (bare uden affekt).
"""
from __future__ import annotations

import core.services.central_affect as central_affect
from core.services import central_trace
from core.services.central_core import Central


def _fresh_central():
    sink = central_trace.TraceSink()
    return Central(sink=sink, emit=lambda k, p: None), sink


def test_observe_tags_flag_event_uro():
    c, sink = _fresh_central()
    c.observe({
        "cluster": "agent", "nerve": "run_error", "kind": "flag",
        "value": 1, "flagged": True,
    })
    recs = sink.recent(limit=5)
    assert recs, "observe should have recorded a trace"
    rec = recs[-1]
    assert rec.payload.get("affect") == "uro"
    assert 0.0 <= rec.payload.get("affect_intensity", -1) <= 1.0


def test_observe_tags_quiet_liveness_ro():
    c, sink = _fresh_central()
    c.observe({"cluster": "heartbeat", "nerve": "liveness", "value": 1.0})
    rec = sink.recent(limit=1)[-1]
    assert rec.payload.get("affect") == "ro"


def test_observe_tags_cost_tryk():
    c, sink = _fresh_central()
    c.observe({"cluster": "cost", "nerve": "daily", "value": 12.5})
    rec = sink.recent(limit=1)[-1]
    assert rec.payload.get("affect") == "tryk"


def test_observe_never_breaks_when_classifier_raises(monkeypatch):
    c, sink = _fresh_central()

    def _boom(*a, **k):
        raise RuntimeError("classifier exploded")

    monkeypatch.setattr(central_affect, "classify_affect", _boom)
    # MÅ IKKE kaste — observe er hot-path.
    c.observe({"cluster": "tool", "nerve": "exec", "value": 1.0})
    recs = sink.recent(limit=1)
    # Trace-record'en blev stadig gemt (affekt fejlede blot stille).
    assert recs, "observe must still record the trace even if affect raises"
    assert recs[-1].cluster == "tool"


def test_observe_self_safe_on_garbage_event():
    c, sink = _fresh_central()
    # ingen kast selv med tom/skør input
    c.observe({})
    c.observe(None)  # type: ignore[arg-type]
