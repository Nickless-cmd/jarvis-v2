"""Tests for start_user_run_detached (live session-broadcast A3).

Dækker nudge-landminen: et ægte nyt run nulstiller follow-bufferen (begin_follow)
og tee'er sine frames; en nudge (der allerede er en aktiv follow-buffer) gør
INGEN af delene — den driver bare iteratoren så followup'en injiceres i det
aktive run, mens det aktive runs egen tråd ejer bufferen.
"""
from __future__ import annotations

import time
from unittest import mock


def _make_async_iter(items):
    async def _gen():
        for item in items:
            yield item
    return _gen()


def _patch_deps(monkeypatch, *, active: bool, frames):
    import core.services.run_follow as rf
    import core.services.visible_runs as vr
    import core.services.visible_runs_sse_v2 as v2

    begin = mock.Mock()
    end = mock.Mock()
    pub = mock.Mock()
    monkeypatch.setattr(rf, "has_active_follow", lambda sid: active)
    monkeypatch.setattr(rf, "begin_follow", begin)
    monkeypatch.setattr(rf, "end_follow", end)
    monkeypatch.setattr(rf, "publish_follow_frame", pub)
    monkeypatch.setattr(vr, "start_visible_run", lambda **kw: _make_async_iter([]))
    monkeypatch.setattr(
        v2, "translate_to_v2", lambda it, **kw: _make_async_iter(frames)
    )
    return begin, end, pub


def test_fresh_run_resets_buffer_and_tees(monkeypatch):
    begin, end, pub = _patch_deps(monkeypatch, active=False, frames=["f1", "f2", "f3"])
    from core.services.visible_runs_sections.detached_run import (
        start_user_run_detached,
    )

    sid = start_user_run_detached(
        message="hej", session_id="s1", eff_model="m", eff_provider="p", lane="l"
    )
    assert sid == "s1"
    # Fresh → bufferen nulstilles SYNKRONT før retur (klientens follow ser frisk buffer).
    begin.assert_called_once()
    assert begin.call_args[0][0] == "s1"
    # Tråden tee'er alle frames + ender bufferen.
    for _ in range(60):
        if pub.call_count >= 3 and end.called:
            break
        time.sleep(0.05)
    assert pub.call_count == 3
    assert end.called


def test_nudge_does_not_reset_or_tee(monkeypatch):
    begin, end, pub = _patch_deps(monkeypatch, active=True, frames=["f1", "f2"])
    from core.services.visible_runs_sections.detached_run import (
        start_user_run_detached,
    )

    sid = start_user_run_detached(
        message="er du der?", session_id="s1", eff_model="m", eff_provider="p", lane="l"
    )
    assert sid == "s1"
    # Nudge → bufferen må IKKE nulstilles (det aktive run ejer den).
    begin.assert_not_called()
    # Giv tråden tid; den må hverken tee eller ende bufferen.
    time.sleep(0.4)
    pub.assert_not_called()
    end.assert_not_called()
