"""Tests for trace-sink: volumen-tolerant ring-buffer, nøglet på run_id."""
from __future__ import annotations

from core.services.central_trace import TraceRecord, TraceSink, sink


def _rec(run_id="r1", nerve="n", kind="decide"):
    return TraceRecord(run_id=run_id, session_id="s", cluster="loop", nerve=nerve, kind=kind)


def test_records_for_run_filters_by_run_id():
    sk = TraceSink(maxlen=100)
    sk.record(_rec(run_id="r1", nerve="a"))
    sk.record(_rec(run_id="r2", nerve="b"))
    sk.record(_rec(run_id="r1", nerve="c"))
    got = sk.records_for_run("r1")
    assert [r.nerve for r in got] == ["a", "c"]


def test_ringbuffer_drops_oldest_beyond_maxlen():
    sk = TraceSink(maxlen=3)
    for i in range(5):
        sk.record(_rec(run_id=str(i)))
    recent = sk.recent(limit=10)
    assert len(recent) == 3
    assert [r.run_id for r in recent] == ["2", "3", "4"]


def test_sink_singleton_is_stable():
    assert sink() is sink()
