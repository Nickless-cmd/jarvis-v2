from __future__ import annotations

import asyncio
import time
from types import SimpleNamespace


def test_start_autonomous_stream_run_relays_frames_for_live_session(
    isolated_runtime,
    monkeypatch,
) -> None:
    import core.services.run_event_log as rel
    import core.services.run_follow as follow
    import core.services.visible_runs as visible_runs
    import core.services.visible_runs_sse_v2 as v2
    from core.services.autonomous_stream_run import start_autonomous_stream_run

    monkeypatch.setattr(
        visible_runs,
        "load_settings",
        lambda: SimpleNamespace(
            primary_model_lane="visible",
            autonomous_model_provider="test-auto-provider",
            autonomous_model_name="test-auto-model",
        ),
    )

    async def _fake_stream(run):
        yield "legacy-frame"

    async def _fake_translate(source, **kwargs):
        await asyncio.sleep(0.1)
        async for _ in source:
            yield "v2-frame"

    monkeypatch.setattr(visible_runs, "_stream_visible_run", _fake_stream)
    monkeypatch.setattr(v2, "translate_to_v2", _fake_translate)

    start_autonomous_stream_run(
        "Stream this wakeup",
        session_id="session-autonomous-relay-test",
        origin="wakeup",
    )

    run_id = rel.active_run_for_session("session-autonomous-relay-test")
    assert run_id is not None
    assert "session-autonomous-relay-test" in follow.live_sessions()
    deadline = time.time() + 2.0
    frames, done = [], False
    while time.time() < deadline:
        frames, done = rel.read(run_id, 0)
        if frames and done:
            break
        time.sleep(0.05)

    assert frames == ["v2-frame"]
    assert done is True
    assert "session-autonomous-relay-test" not in follow.live_sessions()
