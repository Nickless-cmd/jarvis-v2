"""Tests for heartbeat_runtime daemon wiring."""


def test_associative_recall_daemon_registered():
    """Verify associative_recall is registered in daemon_manager registry."""
    from core.services.daemon_manager import _REGISTRY

    assert "associative_recall" in _REGISTRY
    entry = _REGISTRY["associative_recall"]
    assert entry["module"] == "core.services.associative_recall"
    assert entry["default_cadence_minutes"] == 2
    assert entry["default_enabled"] is True


def test_associative_recall_tick_function_exists():
    """Verify tick_associative_recall is importable from associative_recall module."""
    from core.services.associative_recall import tick_associative_recall

    assert callable(tick_associative_recall)


def test_safe_surface_observes_to_central(monkeypatch):
    """Bjørn 2026-06-23: hver cognitive-surface skal OGSÅ observeres til Centralen (indre liv,
    ikke kun gates). _safe_surface fyrer cognitive_surface; throttlet pr. surface."""
    import core.services.heartbeat_runtime as hr
    from core.services.central_core import central
    hr._SURFACE_OBSERVE_AT.clear()
    fired = []
    monkeypatch.setattr(central(), "observe",
                        lambda ev: fired.append(ev) if isinstance(ev, dict) else None)
    d = {}
    hr._safe_surface(d, "soul", lambda: {"active": True})
    hr._safe_surface(d, "soul", lambda: {"active": True})  # throttlet → ingen 2. fyring
    surface_fires = [e for e in fired if e.get("nerve") == "cognitive_surface"]
    assert len(surface_fires) == 1
    assert surface_fires[0]["surface"] == "soul" and surface_fires[0]["cluster"] == "cognition"
    assert surface_fires[0]["active"] is True


def test_safe_surface_reports_failed_surface(monkeypatch):
    import core.services.heartbeat_runtime as hr
    from core.services.central_core import central
    hr._SURFACE_OBSERVE_AT.clear()
    fired = []
    monkeypatch.setattr(central(), "observe",
                        lambda ev: fired.append(ev) if isinstance(ev, dict) else None)
    d = {}
    hr._safe_surface(d, "broken", lambda: (_ for _ in ()).throw(RuntimeError("nej")))
    sf = [e for e in fired if e.get("nerve") == "cognitive_surface"]
    assert sf and sf[0]["active"] is False  # fejlet surface markeres inaktiv
    assert d["broken"]["error"] == "surface-build-failed"  # surface-bygning stadig self-safe


# --- Schedule un-wedge: idle-beat avancerer skemaet (Bjørn 18. aug 2026, A) ---
from datetime import UTC, datetime, timedelta


def _write_state(db, *, schedule_state, last_tick_at, next_tick_at, recovery_status):
    db.upsert_heartbeat_runtime_state(
        state_id="default", last_tick_id="t", last_tick_at=last_tick_at,
        next_tick_at=next_tick_at, schedule_state=schedule_state, due=(schedule_state == "due"),
        last_decision_type="noop", last_result="", blocked_reason="", currently_ticking=False,
        last_trigger_source="startup-recovery", scheduler_active=True, scheduler_started_at="",
        scheduler_stopped_at="", scheduler_health="running", recovery_status=recovery_status,
        last_recovery_at="", provider="ollama", model="m", lane="local", model_source="s",
        resolution_status="ok", fallback_used=False, execution_status="success",
        parse_status="success", budget_status="bounded", last_ping_eligible=False,
        last_ping_result="", last_action_type="", last_action_status="noop",
        last_action_summary="", last_action_artifact="", updated_at=last_tick_at,
    )


def test_idle_beat_advancerer_wedget_skema(isolated_runtime):
    """Wedge: schedule permanent 'due' + recovery 'startup-recovery-pending' (idle-beat
    avancerede ikke). Helperen skal avancere last_tick_at + rydde recovery."""
    hb = isolated_runtime.heartbeat_runtime
    db = isolated_runtime.db
    old = (datetime.now(UTC) - timedelta(hours=6)).isoformat()
    _write_state(db, schedule_state="due", last_tick_at=old, next_tick_at=old,
                 recovery_status="startup-recovery-pending")

    hb._advance_schedule_after_idle_beat(name="default")

    st = db.get_heartbeat_runtime_state()
    assert st["last_tick_at"] > old            # skemaet avancerede
    assert st["recovery_status"] == "idle"     # recovery ryddet
    assert st["schedule_state"] != "due"       # ikke længere permanent due


def test_idle_beat_rører_ikke_ikke_due_skema(isolated_runtime):
    """Hvis den fulde tick allerede avancerede skemaet (ikke 'due'), skal helperen intet gøre."""
    hb = isolated_runtime.heartbeat_runtime
    db = isolated_runtime.db
    fresh = datetime.now(UTC).isoformat()
    future = (datetime.now(UTC) + timedelta(minutes=180)).isoformat()
    _write_state(db, schedule_state="scheduled", last_tick_at=fresh, next_tick_at=future,
                 recovery_status="startup-recovery-completed")

    hb._advance_schedule_after_idle_beat(name="default")

    st = db.get_heartbeat_runtime_state()
    assert st["last_tick_at"] == fresh          # urørt (den fulde tick ejer avanceringen)
    assert st["recovery_status"] == "startup-recovery-completed"
