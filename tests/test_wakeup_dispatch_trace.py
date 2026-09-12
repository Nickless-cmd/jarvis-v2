"""Wakeup-dispatcherens spor + awareness-skelnen — 12/9-2026.

Baggrund (målt, ikke gættet): wake-d07eaea13d fyrede 16:57:35 midt i en aktiv
tur. Den blev ALDRIG dispatchet — intet `dispatched`-flag, intet autonomt run,
ingen nudge — men den stod alligevel som 'fired' i awareness uden forklaring.
wake-bc9c4ebdbc (samme dag, ingen aktiv tur) blev dispatchet: flag sat +0,76 s
efter fired_at, med et autonomt run.

Koden kunne ikke skelne de to. `if not run_started: continue` sprang `_save()`
over, så sporet forsvandt. Disse tests låser at sporet bliver efterladt, at
awareness-linjen siger det højt, og at Bjørns `extra` bæres med hele vejen.
"""
from __future__ import annotations

import types
from datetime import UTC, datetime, timedelta

import pytest

import core.services.self_wakeup as sw
import core.services.wakeup_dispatcher as wd


def _past() -> str:
    return (datetime.now(UTC) - timedelta(seconds=10)).isoformat()


@pytest.fixture
def isolated(monkeypatch):
    """Isolér dispatcheren: ingen nudge, ingen heartbeat, ingen DB-session."""
    monkeypatch.setattr(
        "core.runtime.settings.load_settings",
        lambda: types.SimpleNamespace(nudge_system_enabled=False),
    )
    monkeypatch.setattr(
        "core.services.notification_bridge.send_session_notification",
        lambda *a, **k: None,
    )
    monkeypatch.setattr(
        "core.services.heartbeat_phases.tick_with_phases",
        lambda *a, **k: None,
    )
    monkeypatch.setattr(wd, "pick_wakeup_run_target", lambda **k: "sess-1")


# ── Punkt 1: sporet efterlades når runnet ikke starter ─────────────


def test_dispatch_leaves_skip_trace_when_run_fails(monkeypatch, isolated):
    """Starter det autonome run ikke, skal recorden bære HVORFOR — ikke tie."""
    state = [{
        "wakeup_id": "w1", "status": "pending", "fire_at": _past(),
        "prompt": "Tjek X", "reason": "r1", "channel": "app",
    }]
    monkeypatch.setattr(sw, "_load", lambda: list(state))
    monkeypatch.setattr(sw, "_save", lambda r: state.clear() or state.extend(r))

    def boom(*a, **k):
        raise RuntimeError("no run today")

    monkeypatch.setattr(
        "core.services.autonomous_stream_run.start_autonomous_stream_run", boom
    )

    result = wd.dispatch_due_wakeups()

    assert result["dispatched"] == 0
    assert result["skipped"] == 1
    assert result["skipped_ids"] == ["w1"]
    rec = state[0]
    assert rec["dispatch_skipped"] is True
    assert "run_start_failed" in rec["dispatch_skipped_reason"]
    assert rec.get("dispatched") is not True
    assert rec["dispatch_skipped_at"]


def test_dispatch_marks_dispatched_when_run_starts(monkeypatch, isolated):
    """Den sunde vej: run starter → dispatched-flag, intet skip-spor."""
    state = [{
        "wakeup_id": "w2", "status": "pending", "fire_at": _past(),
        "prompt": "Tjek Y", "reason": "r2", "channel": "app",
    }]
    monkeypatch.setattr(sw, "_load", lambda: list(state))
    monkeypatch.setattr(sw, "_save", lambda r: state.clear() or state.extend(r))
    monkeypatch.setattr(
        "core.services.autonomous_stream_run.start_autonomous_stream_run",
        lambda *a, **k: None,
    )

    result = wd.dispatch_due_wakeups()

    assert result["dispatched"] == 1
    assert result["skipped"] == 0
    rec = state[0]
    assert rec["dispatched"] is True
    assert rec.get("dispatch_skipped") is not True


# ── Punkt 2: awareness-linjen skelner de to ────────────────────────


def test_section_marks_undispatched_wakeup(monkeypatch):
    monkeypatch.setattr(sw, "due_wakeups", lambda **kw: [{
        "wakeup_id": "w1", "status": "fired", "prompt": "Tjek X", "reason": "r",
        "dispatch_skipped": True,
        "dispatch_skipped_reason": "run_start_failed: no run today",
    }])
    section = sw.self_wakeup_section()
    assert section is not None
    assert "IKKE dispatchet" in section
    assert "run_start_failed" in section


def test_section_omits_skip_marker_when_dispatched(monkeypatch):
    monkeypatch.setattr(sw, "due_wakeups", lambda **kw: [{
        "wakeup_id": "w2", "status": "fired", "prompt": "Tjek Y", "reason": "r",
        "dispatched": True,
    }])
    section = sw.self_wakeup_section()
    assert section is not None
    assert "IKKE dispatchet" not in section


# ── Punkt 3: Bjørns extra bæres med ───────────────────────────────


def test_add_wakeup_extra_appends(monkeypatch):
    state = [{"wakeup_id": "w1", "status": "fired", "prompt": "p", "extra": "første"}]
    monkeypatch.setattr(sw, "_load", lambda: list(state))
    monkeypatch.setattr(sw, "_save", lambda r: state.clear() or state.extend(r))

    res = sw.add_wakeup_extra("w1", "anden")

    assert res["status"] == "ok"
    assert state[0]["extra"] == "første\nanden"
    assert state[0]["extra_updated_at"]


def test_add_wakeup_extra_rejects_consumed(monkeypatch):
    state = [{"wakeup_id": "w1", "status": "consumed", "prompt": "p"}]
    monkeypatch.setattr(sw, "_load", lambda: list(state))
    monkeypatch.setattr(sw, "_save", lambda r: None)
    res = sw.add_wakeup_extra("w1", "for sent")
    assert res["status"] == "error"


def test_section_shows_extra(monkeypatch):
    monkeypatch.setattr(sw, "due_wakeups", lambda **kw: [{
        "wakeup_id": "w1", "status": "fired", "prompt": "Tjek X", "reason": "r",
        "extra": "husk at tjekke Y",
    }])
    section = sw.self_wakeup_section()
    assert section is not None
    assert "husk at tjekke Y" in section


def test_dispatch_carries_extra_into_directive(monkeypatch, isolated):
    """Extra skal ende i self_directive — ellers dør den i recorden."""
    captured: dict[str, str] = {}
    state = [{
        "wakeup_id": "w3", "status": "pending", "fire_at": _past(),
        "prompt": "Tjek Z", "reason": "r3", "channel": "app",
        "extra": "husk at tjekke Y",
    }]
    monkeypatch.setattr(sw, "_load", lambda: list(state))
    monkeypatch.setattr(sw, "_save", lambda r: state.clear() or state.extend(r))
    monkeypatch.setattr(
        "core.services.autonomous_stream_run.start_autonomous_stream_run",
        lambda msg, **k: captured.__setitem__("msg", msg),
    )

    result = wd.dispatch_due_wakeups()

    assert result["dispatched"] == 1
    assert "husk at tjekke Y" in captured["msg"]


def test_schedule_persists_extra(monkeypatch):
    state: list = []
    monkeypatch.setattr(sw, "_load", lambda: list(state))
    monkeypatch.setattr(sw, "_save", lambda r: state.clear() or state.extend(r))
    res = sw.schedule_self_wakeup(
        delay_seconds=120, prompt="resume X", reason="t", extra="husk Y",
    )
    assert res["status"] == "ok"
    assert res["wakeup"]["extra"] == "husk Y"


# ── Punkt 4: aktiv-guarden (12/9-2026) ─────────────────────────────
#
# Målt: wake-d07eaea13d fyrede 16:57:35, mens Bjørn skrev 16:58:01 — 26 s efter
# han selv tog ordet. Nu skal dispatcheren NÆGTE at starte et konkurrerende run
# i den session, efterlade sporet 'user_active', og lade awareness-vejen bære
# instruktionerne inde i den aktive tur i stedet.


def _active_state(*, session: str = "sess-1", age_s: float = 1.0) -> dict:
    ts = (datetime.now(UTC) - timedelta(seconds=age_s)).isoformat()
    return {
        "active": True,
        "run_id": "visible-abc",
        "session_id": session,
        "started_at": ts,
        "last_activity_at": ts,
    }


def _patch_active(monkeypatch, state) -> None:
    monkeypatch.setattr(
        "core.services.visible_runs._get_active_visible_run_state",
        lambda: state,
    )


def _wakeup_record(**over) -> dict:
    rec = {
        "wakeup_id": "w1", "status": "pending", "fire_at": _past(),
        "prompt": "Tjek X", "reason": "r1", "channel": "app",
    }
    rec.update(over)
    return rec


def test_guard_skips_run_when_user_turn_active(monkeypatch, isolated):
    """Kernen: aktiv tur i samme session → INTET autonomt run, men et spor."""
    started: list = []
    state = [_wakeup_record(session_id="sess-1")]
    monkeypatch.setattr(sw, "_load", lambda: list(state))
    monkeypatch.setattr(sw, "_save", lambda r: state.clear() or state.extend(r))
    _patch_active(monkeypatch, _active_state(session="sess-1"))
    monkeypatch.setattr(
        "core.services.autonomous_stream_run.start_autonomous_stream_run",
        lambda *a, **k: started.append(a),
    )

    result = wd.dispatch_due_wakeups()

    assert started == [], "der blev startet et run oveni en aktiv tur"
    assert result["dispatched"] == 0
    assert result["skipped"] == 1
    assert state[0]["dispatch_skipped"] is True
    assert state[0]["dispatch_skipped_reason"] == "user_active"


def test_guard_allows_run_when_other_session_active(monkeypatch, isolated):
    """Aktiv tur i en ANDEN session er ikke «du taler her» → run må starte."""
    started: list = []
    state = [_wakeup_record(session_id="sess-1")]
    monkeypatch.setattr(sw, "_load", lambda: list(state))
    monkeypatch.setattr(sw, "_save", lambda r: state.clear() or state.extend(r))
    _patch_active(monkeypatch, _active_state(session="sess-OTHER"))
    monkeypatch.setattr(
        "core.services.autonomous_stream_run.start_autonomous_stream_run",
        lambda *a, **k: started.append(a),
    )

    result = wd.dispatch_due_wakeups()

    assert len(started) == 1
    assert result["dispatched"] == 1


def test_guard_allows_run_when_active_turn_is_stale(monkeypatch, isolated):
    """Et run der ikke har rørt sig i >120 s er ikke «nogen taler nu»."""
    started: list = []
    state = [_wakeup_record(session_id="sess-1")]
    monkeypatch.setattr(sw, "_load", lambda: list(state))
    monkeypatch.setattr(sw, "_save", lambda r: state.clear() or state.extend(r))
    _patch_active(monkeypatch, _active_state(session="sess-1", age_s=600))
    monkeypatch.setattr(
        "core.services.autonomous_stream_run.start_autonomous_stream_run",
        lambda *a, **k: started.append(a),
    )

    result = wd.dispatch_due_wakeups()

    assert len(started) == 1
    assert result["dispatched"] == 1


def test_guard_is_self_safe_when_state_unreadable(monkeypatch, isolated):
    """Kunne aktiv-tilstanden ikke læses, må wakeup'en IKKE forsvinde."""
    started: list = []
    state = [_wakeup_record(session_id="sess-1")]
    monkeypatch.setattr(sw, "_load", lambda: list(state))
    monkeypatch.setattr(sw, "_save", lambda r: state.clear() or state.extend(r))

    def boom():
        raise RuntimeError("db nede")

    monkeypatch.setattr(
        "core.services.visible_runs._get_active_visible_run_state", boom
    )
    monkeypatch.setattr(
        "core.services.autonomous_stream_run.start_autonomous_stream_run",
        lambda *a, **k: started.append(a),
    )

    result = wd.dispatch_due_wakeups()

    assert len(started) == 1, "guarden slugte wakeup'en da DB'en fejlede"
    assert result["dispatched"] == 1


def test_user_active_skip_is_not_retried(monkeypatch, isolated):
    """En user_active-afvisning må ikke prøve igen ved hver tick."""
    started: list = []
    state = [_wakeup_record(
        dispatch_skipped=True, dispatch_skipped_reason="user_active",
    )]
    monkeypatch.setattr(sw, "_load", lambda: list(state))
    monkeypatch.setattr(sw, "_save", lambda r: state.clear() or state.extend(r))
    _patch_active(monkeypatch, _active_state(session="sess-1"))
    monkeypatch.setattr(
        "core.services.autonomous_stream_run.start_autonomous_stream_run",
        lambda *a, **k: started.append(a),
    )

    result = wd.dispatch_due_wakeups()

    assert started == []
    assert result["dispatched"] == 0
    assert result["skipped"] == 0, "den blev behandlet igen — ikke terminal"


def test_section_shows_user_active_reason(monkeypatch):
    """Bjørn skal kunne se at den blev afvist FORDI han var der."""
    monkeypatch.setattr(sw, "due_wakeups", lambda **kw: [{
        "wakeup_id": "w1", "status": "fired", "prompt": "Tjek X", "reason": "r",
        "dispatch_skipped": True, "dispatch_skipped_reason": "user_active",
    }])
    section = sw.self_wakeup_section()
    assert section is not None
    assert "user_active" in section
    assert "IKKE dispatchet" in section


# ── Punkt 5: kvitteret FØR dispatcher-tick (12/9-2026) ─────────────
#
# Sidste stille kant. Dispatcheren filtrerer på status=='fired', så en FYRET
# wakeup der kvitteres før næste 60 s-tick er usynlig for den: hverken
# `dispatched` eller `dispatch_skipped` nåede at blive sat. Instruktionerne
# overlevede (awareness bar dem), men sporet manglede. Sporet sættes nu ved
# kvitteringen — det eneste sted der VED at den fyrede ubehandlet.


def test_consume_before_dispatch_leaves_trace(monkeypatch):
    """Fyret + kvitteret uden dispatch → sporet skal stå på recorden."""
    state = [{
        "wakeup_id": "w1", "status": "fired", "prompt": "Tjek X",
        "reason": "r", "fired_at": _past(),
    }]
    monkeypatch.setattr(sw, "_load", lambda: list(state))
    monkeypatch.setattr(sw, "_save", lambda r: state.clear() or state.extend(r))

    res = sw.mark_wakeup_consumed("w1")

    assert res["status"] == "ok"
    assert state[0]["status"] == "consumed"
    assert state[0]["consumed_without_dispatch"] is True
    assert state[0]["consumed_without_dispatch_reason"] == "consumed_before_dispatch_tick"


def test_consume_after_dispatch_leaves_no_trace(monkeypatch):
    """Blev den dispatchet, er der intet hul at dække."""
    state = [{"wakeup_id": "w1", "status": "fired", "prompt": "p", "dispatched": True}]
    monkeypatch.setattr(sw, "_load", lambda: list(state))
    monkeypatch.setattr(sw, "_save", lambda r: state.clear() or state.extend(r))

    sw.mark_wakeup_consumed("w1")

    assert state[0].get("consumed_without_dispatch") is not True


def test_consume_after_skip_leaves_no_trace(monkeypatch):
    """Blev den afvist MED spor (user_active), er den allerede forklaret."""
    state = [{
        "wakeup_id": "w1", "status": "fired", "prompt": "p",
        "dispatch_skipped": True, "dispatch_skipped_reason": "user_active",
    }]
    monkeypatch.setattr(sw, "_load", lambda: list(state))
    monkeypatch.setattr(sw, "_save", lambda r: state.clear() or state.extend(r))

    sw.mark_wakeup_consumed("w1")

    assert state[0].get("consumed_without_dispatch") is not True


def test_consume_pending_leaves_no_trace(monkeypatch):
    """En wakeup der aldrig fyrede har intet dispatch at mangle."""
    state = [{"wakeup_id": "w1", "status": "pending", "prompt": "p"}]
    monkeypatch.setattr(sw, "_load", lambda: list(state))
    monkeypatch.setattr(sw, "_save", lambda r: state.clear() or state.extend(r))

    sw.mark_wakeup_consumed("w1")

    assert state[0].get("consumed_without_dispatch") is not True


def test_consume_before_tick_is_invisible_to_dispatcher(monkeypatch, isolated):
    """Bevis på hullet selv: dispatcheren ser INTET når den kvitteres først —
    og netop derfor skal sporet sættes ved kvitteringen, ikke af dispatcheren."""
    state = [{
        "wakeup_id": "w1", "status": "fired", "fired_at": _past(),
        "prompt": "Tjek X", "reason": "r", "channel": "app",
    }]
    monkeypatch.setattr(sw, "_load", lambda: list(state))
    monkeypatch.setattr(sw, "_save", lambda r: state.clear() or state.extend(r))
    monkeypatch.setattr(
        "core.services.autonomous_stream_run.start_autonomous_stream_run",
        lambda *a, **k: None,
    )

    sw.mark_wakeup_consumed("w1")          # kvitteret FØR dispatcheren ser den
    result = wd.dispatch_due_wakeups()     # tick'en kommer bagefter

    assert result["dispatched"] == 0
    assert result.get("skipped", 0) == 0, "dispatcheren behandlede en kvitteret wakeup"
    rec = state[0]
    assert rec.get("dispatched") is None
    assert rec.get("dispatch_skipped") is None
    assert rec["consumed_without_dispatch"] is True
