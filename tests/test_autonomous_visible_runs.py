from __future__ import annotations

import time
from types import SimpleNamespace

from core.eventbus.bus import event_bus


def test_start_autonomous_run_publishes_persistent_audit_events(
    isolated_runtime,
    monkeypatch,
) -> None:
    visible_runs = __import__(
        "apps.api.jarvis_api.services.visible_runs",
        fromlist=["start_autonomous_run"],
    )

    monkeypatch.setattr(
        visible_runs,
        "load_settings",
        lambda: SimpleNamespace(
            primary_model_lane="visible",
            visible_model_provider="test-provider",
            visible_model_name="test-model",
        ),
    )

    async def _fake_stream(run):
        yield "one-frame"

    monkeypatch.setattr(visible_runs, "_stream_visible_run", _fake_stream)

    visible_runs.start_autonomous_run(
        "Inspect persistent autonomous audit",
        session_id="session-autonomous-test",
    )

    deadline = time.time() + 2.0
    kinds: set[str] = set()
    while time.time() < deadline:
        kinds = {
            str(event.get("kind") or "")
            for event in event_bus.recent(limit=20)
            if str((event.get("payload") or {}).get("session_id") or "")
            == "session-autonomous-test"
        }
        if {
            "runtime.autonomous_run_started",
            "runtime.autonomous_run_completed",
        }.issubset(kinds):
            break
        time.sleep(0.05)

    assert "runtime.autonomous_run_started" in kinds
    assert "runtime.autonomous_run_completed" in kinds
