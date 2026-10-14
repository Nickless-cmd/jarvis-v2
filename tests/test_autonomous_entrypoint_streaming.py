from __future__ import annotations

import asyncio
import threading
import time
from types import SimpleNamespace

import pytest


@pytest.mark.parametrize("follow", [False, True])
def test_autonomous_entrypoint_always_registers_authoritative_v2_frame_log(
    isolated_runtime,
    monkeypatch,
    follow: bool,
) -> None:
    import core.services.run_event_log as relay
    import core.services.visible_runs as visible_runs
    import core.services.visible_runs_sse_v2 as v2

    monkeypatch.setattr(
        visible_runs,
        "load_settings",
        lambda: SimpleNamespace(
            primary_model_lane="visible",
            autonomous_model_provider="test-auto-provider",
            autonomous_model_name="test-auto-model",
        ),
    )

    release = threading.Event()

    async def _fake_stream(run):
        yield "legacy-frame"

    async def _fake_translate(source, **kwargs):
        while not release.is_set():
            await asyncio.sleep(0.01)
        async for _ in source:
            yield "v2-frame"

    monkeypatch.setattr(visible_runs, "_stream_visible_run", _fake_stream)
    monkeypatch.setattr(v2, "translate_to_v2", _fake_translate)

    session_id = f"session-autonomous-entrypoint-{follow}"
    visible_runs.start_autonomous_run(
        "Persist this autonomous stream",
        session_id=session_id,
        follow=follow,
    )

    try:
        run_id = relay.active_run_for_session(session_id)
        assert run_id is not None
    finally:
        release.set()

    deadline = time.time() + 2.0
    frames, done = [], False
    while time.time() < deadline:
        frames, done = relay.read(run_id, 0)
        if frames and done:
            break
        time.sleep(0.02)

    assert frames == ["v2-frame"]
    assert done is True
