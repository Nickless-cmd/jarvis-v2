"""Boy Scout: autonom run-starter udskilt fra visible_runs - re-eksporten og opslaget ved kald bevarer adfaerden."""
from __future__ import annotations

import time
from types import SimpleNamespace

from core.eventbus.bus import event_bus


def test_visible_runs_re_exports_the_very_same_objects():
    from core.services import visible_autonomous_run as new
    from core.services import visible_runs as old
    assert old.start_autonomous_run is new.start_autonomous_run
    assert old._observe_autonomous_run is new._observe_autonomous_run


def test_a_patch_on_visible_runs_still_steers_the_moved_starter(isolated_runtime, monkeypatch):
    """load_settings og _stream_visible_run slaas op paa visible_runs ved KALDET, ikke ved import."""
    from core.services import visible_runs as vr
    seen = {"settings": 0, "frames": 0}

    def settings():
        seen["settings"] += 1
        return SimpleNamespace(primary_model_lane="visible", visible_model_provider="p", visible_model_name="m",
                               autonomous_model_provider="ap", autonomous_model_name="am")

    async def stream(run):
        seen["frames"] += 1
        yield "frame"

    monkeypatch.setattr(vr, "load_settings", settings)
    monkeypatch.setattr(vr, "_stream_visible_run", stream)
    vr.start_autonomous_run("flyt-test", session_id="sess-boyscout")
    deadline = time.time() + 3.0
    kinds: set[str] = set()
    while time.time() < deadline and "runtime.autonomous_run_completed" not in kinds:
        kinds = {str(e.get("kind") or "") for e in event_bus.recent(limit=30)
                 if str((e.get("payload") or {}).get("session_id") or "") == "sess-boyscout"}
        time.sleep(0.05)
    assert seen == {"settings": 1, "frames": 1}
    assert {"runtime.autonomous_run_started", "runtime.autonomous_run_completed"} <= kinds
