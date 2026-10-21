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


def test_vaekning_arver_samtalens_permissions(isolated_runtime, monkeypatch) -> None:
    """Målt 21/10-2026 (Bjørn: «et wakeup skal fortsætte som det allerede er sat»).

    En vækning i en `trust`-samtale skal have `trust_all=True` på runnet.
    Uden det rejser den et godkendelses-kort som ingen sad og svarede på —
    og uden `force` når godkendelsen aldrig `_runtime_trust_all`, så
    kommandoen blev godkendt uden nogensinde at være kørt.

    MUTATION: fjern `trust_all=_trust_for_session(sid)` fra run-oprettelsen
    i `autonomous_stream_run` → fanget["trust_all"] er False → testen fejler.
    """
    from types import SimpleNamespace

    import core.services.autonomous_stream_run as asr
    import core.services.visible_runs as visible_runs

    fanget: dict = {}

    class _FakeRun:
        def __init__(self, **kw):
            fanget.update(kw)
            self.run_id = str(kw.get("run_id") or "r")
            self.session_id = str(kw.get("session_id") or "")
            self.user_message = str(kw.get("user_message") or "")
            self.autonomous = bool(kw.get("autonomous", False))
            self.trust_all = bool(kw.get("trust_all", False))
            self.origin = str(kw.get("origin") or "")
            self.provider = str(kw.get("provider") or "")
            self.model = str(kw.get("model") or "")
            self.lane = str(kw.get("lane") or "")

    async def _tom_stream(run):
        if False:  # pragma: no cover — gør den til en async generator
            yield ""

    monkeypatch.setattr(
        visible_runs,
        "load_settings",
        lambda: SimpleNamespace(
            primary_model_lane="visible",
            autonomous_model_provider="p",
            autonomous_model_name="m",
        ),
    )
    monkeypatch.setattr(visible_runs, "VisibleRun", _FakeRun)
    monkeypatch.setattr(visible_runs, "_stream_visible_run", _tom_stream)
    monkeypatch.setattr(asr, "_trust_for_session", lambda sid: True)

    asr.start_autonomous_stream_run("wake", session_id="s-trust", origin="wakeup")

    assert fanget.get("trust_all") is True, "en vækning skal arve samtalens fulde adgang"
    assert fanget.get("autonomous") is True
