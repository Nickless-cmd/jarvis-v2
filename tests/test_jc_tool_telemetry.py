"""Tests for core/services/jc_tool_telemetry.py — per-tool eventbus
telemetry for jarvis-code's client-driven tool runs (Fase 5 Task 20)."""
from core.services import jc_tool_telemetry


def test_publish_tool_step_calls_event_bus(monkeypatch):
    published = []

    class _FakeBus:
        def publish(self, *, kind, payload):
            published.append((kind, payload))

    monkeypatch.setattr("core.eventbus.bus.event_bus", _FakeBus())
    ok = jc_tool_telemetry.publish_tool_step(tool="bash", status="ok", duration_ms=42.0,
                                             bytes_=100, user_id="u1", session_id="s1")
    assert ok is True
    assert len(published) == 1
    kind, payload = published[0]
    assert kind == "tool.jc_step"
    assert payload["tool"] == "bash"
    assert payload["status"] == "ok"
    assert payload["duration_ms"] == 42.0
    assert payload["user_id"] == "u1"


def test_publish_tool_step_self_safe_on_failure(monkeypatch):
    class _BoomBus:
        def publish(self, **kw):
            raise RuntimeError("eventbus down")

    monkeypatch.setattr("core.eventbus.bus.event_bus", _BoomBus())
    ok = jc_tool_telemetry.publish_tool_step(tool="bash", status="ok")
    assert ok is False   # never raises


def test_publish_tool_steps_batch(monkeypatch):
    published = []

    class _FakeBus:
        def publish(self, *, kind, payload):
            published.append(payload)

    monkeypatch.setattr("core.eventbus.bus.event_bus", _FakeBus())
    steps = [
        {"tool": "bash", "status": "ok", "duration_ms": 10, "bytes": 5},
        {"tool": "read_file", "status": "ok", "duration_ms": 3, "bytes": 200},
    ]
    n = jc_tool_telemetry.publish_tool_steps(steps, user_id="u1", session_id="s1")
    assert n == 2
    assert len(published) == 2
    assert {p["tool"] for p in published} == {"bash", "read_file"}


def test_publish_tool_steps_empty_list(monkeypatch):
    n = jc_tool_telemetry.publish_tool_steps([])
    assert n == 0


def test_publish_tool_steps_one_failure_does_not_drop_rest(monkeypatch):
    calls = {"n": 0}

    class _FlakyBus:
        def publish(self, *, kind, payload):
            calls["n"] += 1
            if calls["n"] == 1:
                raise RuntimeError("boom")

    monkeypatch.setattr("core.eventbus.bus.event_bus", _FlakyBus())
    steps = [{"tool": "a", "status": "ok"}, {"tool": "b", "status": "ok"}]
    n = jc_tool_telemetry.publish_tool_steps(steps)
    assert n == 1   # first failed, second succeeded
