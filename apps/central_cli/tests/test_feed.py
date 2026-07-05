from __future__ import annotations
from central_cli.feed import FeedLine, feed_line_from_event, FeedBuffer


def test_feed_line_from_trace_event():
    ev = {"cluster": "network", "nerve": "health", "decision": "degraded", "reason": "latency"}
    ln = feed_line_from_event(ev)
    assert isinstance(ln, FeedLine)
    assert ln.cluster == "network" and ln.nerve == "health"
    assert ln.decision == "degraded"
    assert "network/health" in ln.text


def test_buffer_is_bounded_and_newest_first():
    buf = FeedBuffer(cap=3)
    for i in range(5):
        buf.add(feed_line_from_event({"cluster": "c", "nerve": str(i), "decision": "observe"}))
    lines = buf.recent()
    assert len(lines) == 3
    assert lines[0].nerve == "4"   # nyeste først
    assert lines[-1].nerve == "2"


def test_severity_color_maps():
    assert feed_line_from_event({"cluster": "c", "nerve": "n", "decision": "error"}).color == "red"
    assert feed_line_from_event({"cluster": "c", "nerve": "n", "decision": "degraded"}).color == "yellow"
    assert feed_line_from_event({"cluster": "c", "nerve": "n", "decision": "observe"}).color == "green"
