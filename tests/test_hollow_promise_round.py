from __future__ import annotations

from core.services import hollow_promise_round as H


def test_tool_choice_required_only_after_hollow_on_supported_provider():
    assert H.next_round_tool_choice(force_summary=False, hollow_force=True, provider="deepseek") == "required"
    assert H.next_round_tool_choice(force_summary=False, hollow_force=True, provider="ollama") is None
    assert H.next_round_tool_choice(force_summary=False, hollow_force=False, provider="deepseek") is None


def test_force_summary_wins():
    assert H.next_round_tool_choice(force_summary=True, hollow_force=True, provider="deepseek") == "none"


def test_events_are_published_and_valid(monkeypatch):
    published: list[tuple[str, dict]] = []
    monkeypatch.setattr("core.eventbus.bus.event_bus.publish", lambda kind, payload=None, **kw: published.append((kind, payload)))
    monkeypatch.setattr("core.services.followup_observer.note_hollow_promise", lambda *a, **k: None)
    H.note_detected(run_id="r", provider="deepseek", model="m", round_index=2, session_id="s", forced=True)
    resolved = H.note_outcome(run_id="r", provider="deepseek", model="m", round_index=3, session_id="s", forced=True, tool_calls=2)
    assert resolved is True
    kinds = [k for k, _ in published]
    assert kinds == ["runtime.hollow_promise_detected", "runtime.hollow_promise_outcome"]
    assert published[1][1]["resolved"] is True and published[1][1]["forced"] is True
    from core.eventbus.events import Event
    for k, p in published:
        Event.create(k, p)  # family 'runtime' is registered → persists


def test_outcome_still_hollow(monkeypatch):
    monkeypatch.setattr("core.eventbus.bus.event_bus.publish", lambda *a, **k: None)
    monkeypatch.setattr("core.services.followup_observer.note_hollow_promise", lambda *a, **k: None)
    assert H.note_outcome(run_id="r", provider="ollama", model="m", round_index=3, session_id="s", forced=False, tool_calls=0) is False
