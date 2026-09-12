"""FULD e2e: wakeup-guarden gennem den ÆGTE job-kø og det registrerede register.

Hvorfor denne fil findes (12/9-2026): de to første wakeup-fix blev bevist med
enhedstests + en MANUEL kalder (`dispatch_due_wakeups()` fra et script). Det er
ikke e2e. Bjørn: «Intet er færdigt før fuld e2e».

Kæden der testes her er den produktionsægte:

    enqueue_job("wakeup_dispatch")        ← periodic_jobs_scheduler
      → run_next_job()                    ← heartbeat_runtime dræner køen
        → _HANDLERS["wakeup_dispatch"]    ← registreret af governance_bootstrap
          → dispatch_due_wakeups()
            → _active_turn_blocks()       ← AKTIV-GUARDEN (commit 612ac66e)
              → skip ('user_active') ELLER start_autonomous_stream_run()
                → self_wakeup_section()   ← awareness-renderingen

Alt er ægte: job-køen, registret, handleren, dispatcheren, guarden, aktiv-
tilstanden (DB) og awareness-sektionen. Kun to ting er isoleret, fordi de
ellers rører verden uden for testen:

  * lager (wakeup-state + job-kø) → tmp/in-memory, så produktionsdata ikke
    forurenes
  * selve LLM-kørslen + nudge/heartbeat → stubbet, fordi et rigtigt run koster
    penge og starter en agent i produktion

Det sidste er den ærlige grænse: alt FØR LLM-kaldet er e2e; selve kaldet er
stubbet og verificeret på argumentet (hvilken session, hvilken tekst).
"""
from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest

import core.services.jobs_engine as je
import core.services.self_wakeup as sw
from core.services.visible_runs_sections import run_control_state as rcs


# ── fixtures ────────────────────────────────────────────────────────────────


class _RunSpy:
    """Fanger om/hvordan det autonome run blev startet (den stubbede kant)."""

    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    def __call__(self, message: str, *, session_id: str | None, origin: str = "autonomous") -> None:
        self.calls.append({"message": message, "session_id": session_id, "origin": origin})

    @property
    def started(self) -> bool:
        return bool(self.calls)


@pytest.fixture
def e2e(monkeypatch, tmp_path):
    """Ægte kæde; kun lager + ydre I/O isoleret."""
    # 1. Wakeup-lager → in-memory
    store: dict[str, list] = {"records": []}
    monkeypatch.setattr(sw, "load_json", lambda key, default=None: list(store["records"]))
    monkeypatch.setattr(
        sw, "save_json", lambda key, value: store.__setitem__("records", list(value))
    )

    # 2. Job-kø → tmp-fil (så produktionskøen ikke forurenes)
    qpath = Path(tmp_path) / "jobs_queue.json"
    monkeypatch.setattr(je, "_storage_path", lambda: qpath)
    je._LOAD_CACHE_KEY = None
    je._LOAD_CACHE_ITEMS = None

    # 3. Registrér de ÆGTE handlers (samme vej som bootstrap gør ved opstart)
    from core.services.governance_bootstrap import ensure_default_job_handlers

    ensure_default_job_handlers()

    # 4. Ydre I/O: nudge, heartbeat, desktop-notifikation → no-op
    import types

    monkeypatch.setattr(
        "core.runtime.settings.load_settings",
        lambda: types.SimpleNamespace(nudge_system_enabled=False),
    )
    monkeypatch.setattr(
        "core.services.notification_bridge.send_session_notification", lambda *a, **k: None
    )
    monkeypatch.setattr("core.services.heartbeat_phases.tick_with_phases", lambda *a, **k: None)

    # 5. Den stubbede kant: selve LLM-kørslen
    spy = _RunSpy()
    monkeypatch.setattr(
        "core.services.autonomous_stream_run.start_autonomous_stream_run", spy
    )

    # 6. Aktiv-tilstand lever i DB'en — gem og gendan, så vi ikke efterlader spor
    saved_active = rcs._get_active_visible_run_state()

    yield types.SimpleNamespace(store=store, spy=spy, run=spy, queue=qpath)

    rcs._set_active_visible_run(saved_active or {})


# ── helpers ─────────────────────────────────────────────────────────────────


def _plant_wakeup(store, *, wid="wake-e2e", session_id="chat-e2e", **over) -> dict[str, Any]:
    """Læg en FORFALDEN wakeup i lageret — samme form som schedule_self_wakeup."""
    past = (datetime.now(UTC) - timedelta(seconds=5)).isoformat()
    rec = {
        "wakeup_id": wid,
        "scheduled_at": past,
        "fire_at": past,          # allerede forfalden → due_wakeups samler den op
        "delay_seconds": 60,
        "prompt": "TJEK: e2e-verifikation",
        "reason": "e2e",
        "extra": None,
        "status": "pending",
        "fired_at": None,
        "consumed_at": None,
        "channel": "app",
        "session_id": session_id,
        "user_id": "1246415163603816499",
        "workspace_name": "bjorn",
        "user_display_name": "Bjørn",
        "role": None,
        "context_channel": "webchat",
    }
    rec.update(over)
    store["records"].append(rec)
    return rec


def _set_active(session_id: str, *, age_s: float = 0.0) -> None:
    """Sæt den DELTE aktiv-tilstand som en kørende tur gør det (DB)."""
    ts = (datetime.now(UTC) - timedelta(seconds=age_s)).isoformat()
    rcs._set_active_visible_run(
        {
            "active": True,
            "run_id": "visible-e2e-active",
            "session_id": session_id,
            "lane": "primary",
            "provider": "ollama",
            "model": "test",
            "started_at": ts,
            "last_activity_at": ts,
            "current_user_message_preview": "e2e",
            "capability_id": None,
            "cancelled": False,
            "updated_at": ts,
        }
    )


def _drain_queue() -> list[Any]:
    """Dræn køen præcis som heartbeat_runtime gør — gennem det ægte run_next_job."""
    out = []
    for _ in range(5):
        res = je.run_next_job()
        if res is None:
            break
        out.append(res)
    return out


def _record(store, wid="wake-e2e") -> dict[str, Any]:
    return next(r for r in store["records"] if r.get("wakeup_id") == wid)


# ── tests ───────────────────────────────────────────────────────────────────


def test_e2e_active_turn_blocks_run_through_real_queue(e2e):
    """En forfalden wakeup i samme session mens turen er aktiv → INTET run."""
    _plant_wakeup(e2e.store, session_id="chat-e2e")
    _set_active("chat-e2e")

    # Den produktionsægte vej: enqueue → dræn køen
    je.enqueue_job(job_type="wakeup_dispatch", payload={"reason": "e2e"}, priority=8)
    results = _drain_queue()

    assert [r.job_type for r in results] == ["wakeup_dispatch"]
    assert results[0].status == "ok"

    rec = _record(e2e.store)
    assert rec["dispatch_skipped"] is True
    assert rec["dispatch_skipped_reason"] == "user_active"
    assert not rec.get("dispatched")
    assert rec["status"] == "fired"          # bæres videre af awareness
    assert e2e.spy.started is False          # ← kernen: intet konkurrerende run


def test_e2e_no_active_turn_dispatches_run_through_real_queue(e2e):
    """Ingen aktiv tur → runnet starter, gennem samme ægte kæde."""
    rcs._set_active_visible_run({})          # ingen aktiv tur
    _plant_wakeup(e2e.store, session_id="chat-e2e")

    je.enqueue_job(job_type="wakeup_dispatch", payload={"reason": "e2e"}, priority=8)
    _drain_queue()

    rec = _record(e2e.store)
    assert rec.get("dispatched") is True
    assert rec.get("dispatch_skipped") is None
    assert e2e.spy.started is True
    assert e2e.spy.calls[0]["session_id"] == "chat-e2e"
    assert e2e.spy.calls[0]["origin"] == "wakeup"
    assert "TJEK: e2e-verifikation" in e2e.spy.calls[0]["message"]


def test_e2e_other_session_does_not_block(e2e):
    """Aktiv i en ANDEN session → wakeup'en hører ikke til der; run må starte."""
    _set_active("chat-anden-session")
    _plant_wakeup(e2e.store, session_id="chat-e2e")

    je.enqueue_job(job_type="wakeup_dispatch", payload={"reason": "e2e"}, priority=8)
    _drain_queue()

    assert e2e.spy.started is True
    assert _record(e2e.store).get("dispatched") is True


def test_e2e_stale_active_turn_does_not_block(e2e):
    """Aktiv-tilstand ældre end freshness-vinduet (120 s) → ikke «nogen taler nu»."""
    _set_active("chat-e2e", age_s=300.0)
    _plant_wakeup(e2e.store, session_id="chat-e2e")

    je.enqueue_job(job_type="wakeup_dispatch", payload={"reason": "e2e"}, priority=8)
    _drain_queue()

    assert e2e.spy.started is True
    assert _record(e2e.store).get("dispatched") is True


def test_e2e_user_active_skip_is_terminal_not_retried(e2e):
    """En afvist wakeup prøves ikke igen på næste tick — men bæres af awareness."""
    rec = _plant_wakeup(e2e.store, session_id="chat-e2e")
    rec["dispatch_skipped"] = True
    rec["dispatch_skipped_reason"] = "user_active"
    rec["dispatch_skipped_at"] = datetime.now(UTC).isoformat()

    rcs._set_active_visible_run({})          # ingen aktiv tur nu

    je.enqueue_job(job_type="wakeup_dispatch", payload={"reason": "e2e"}, priority=8)
    _drain_queue()

    assert e2e.spy.started is False          # IKKE dispatchet igen
    assert _record(e2e.store).get("dispatched") is None
    assert _record(e2e.store)["status"] == "fired"   # awareness bærer den stadig


def test_e2e_awareness_renders_skipped_wakeup_with_marker(e2e):
    """Efter en afvisning skal awareness-linjen sige det HØJT — med extra med."""
    rec = _plant_wakeup(e2e.store, session_id="chat-e2e")
    rec["extra"] = "Bjørns tilføjelse"
    _set_active("chat-e2e")

    je.enqueue_job(job_type="wakeup_dispatch", payload={"reason": "e2e"}, priority=8)
    _drain_queue()

    section = sw.self_wakeup_section()
    assert section is not None
    assert "wake-e2e" in section
    assert "IKKE dispatchet" in section
    assert "user_active" in section
    assert "Bjørns tilføjelse" in section


def test_e2e_extra_flows_into_dispatched_directive(e2e):
    """Bjørns `extra` skal med helt ind i self_directive når runnet starter."""
    rcs._set_active_visible_run({})
    rec = _plant_wakeup(e2e.store, session_id="chat-e2e")
    rec["extra"] = "husk også X"

    je.enqueue_job(job_type="wakeup_dispatch", payload={"reason": "e2e"}, priority=8)
    _drain_queue()

    assert e2e.spy.started is True
    assert "Tilføjelse: husk også X" in e2e.spy.calls[0]["message"]


def test_e2e_queue_is_really_used(e2e):
    """Bevis at køen faktisk er en del af kæden — ikke bare kaldes forbi."""
    je.enqueue_job(job_type="wakeup_dispatch", payload={"reason": "e2e"}, priority=8)
    assert e2e.queue.exists(), "job-køen skal ligge i det isolerede lager"
    data = json.loads(e2e.queue.read_text())
    assert any(j.get("job_type") == "wakeup_dispatch" for j in data)

    results = _drain_queue()
    assert len(results) == 1
    # Jobbet skal være markeret færdigt i køen efter dræning
    after = json.loads(e2e.queue.read_text())
    done = [j for j in after if j.get("job_type") == "wakeup_dispatch"]
    assert done and done[-1].get("status") == "ok"


def test_e2e_consumed_before_tick_leaves_trace(e2e):
    """Sidste stille kant, ende til ende gennem den ÆGTE job-kø.

    Sekvensen er den produktionsægte: wakeup'en forfalder og awareness-vejen
    flipper den pending→fired når Jarvis får en tur; han kvitterer den; og
    FØRST DEREFTER kommer dispatcher-tick'en. Dispatcheren filtrerer på
    status=='fired', så den ser intet — men recorden skal bære sporet.
    """
    _plant_wakeup(e2e.store, session_id="chat-e2e")

    # Awareness-vejen (samme kald prompt-contract bruger) flipper pending→fired
    section = sw.self_wakeup_section()
    assert section is not None
    assert _record(e2e.store)["status"] == "fired"

    # ... og han kvitterer FØR dispatcheren når sit næste tick
    assert sw.mark_wakeup_consumed("wake-e2e")["status"] == "ok"

    # Nu kommer tick'en — gennem den ægte kø
    je.enqueue_job(job_type="wakeup_dispatch", payload={"reason": "e2e"}, priority=8)
    _drain_queue()

    rec = _record(e2e.store)
    assert rec["status"] == "consumed"
    assert e2e.spy.started is False
    assert rec.get("dispatched") is None
    assert rec.get("dispatch_skipped") is None       # dispatcheren så den aldrig
    assert rec["consumed_without_dispatch"] is True  # ... men sporet står der
    assert rec["consumed_without_dispatch_reason"] == "consumed_before_dispatch_tick"
