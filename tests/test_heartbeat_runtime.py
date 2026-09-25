"""Tests for heartbeat_runtime daemon wiring."""


def test_associative_recall_daemon_er_pensioneret_ikke_forsvundet():
    """Den selvstændige daemon blev PENSIONERET 15. juli 2026 → foldet ind i cluster_memory.

    Testen hævdede tidligere `default_enabled is True` og var derfor rød på main lige
    siden pensioneringen — den tredje røde-på-main-test fundet 19. aug. Den beskyttede
    daemonens ADRESSE, ikke dens funktion, og var blevet et fejlsignal man vænnede sig
    til. Vi hævder nu selve pensioneringen, så en utilsigtet gen-tænding også fanges.
    """
    from core.services.daemon_manager import _REGISTRY

    assert "associative_recall" in _REGISTRY
    entry = _REGISTRY["associative_recall"]
    assert entry["module"] == "core.services.associative_recall"
    assert entry["default_enabled"] is False, (
        "den selvstændige daemon er pensioneret — to kilder til samme tick "
        "ville køre associativ recall dobbelt"
    )
    assert entry.get("retired"), "pensioneringen skal stå i registret, ikke kun i en commit"


def test_associativ_recall_koerer_STADIG_via_cluster_memory():
    """Det der betyder noget: at evnen overlevede flytningen.

    Associativ recall er underbevidstheden — den vækker sovende minder ved kontekst.
    Havde pensioneringen tabt den, ville intet have sagt fra: den gamle test tjekkede
    kun et flag på den tomme plads, ikke om nogen havde overtaget arbejdet.
    """
    from core.services.cluster_daemon_families import (
        _MEMORY_UNCONDITIONAL,
        _mem_associative_recall_live,
    )
    from core.services.daemon_manager import _REGISTRY

    names = [n for n, _ in _MEMORY_UNCONDITIONAL]
    assert "associative_recall" in names, "evnen er faldet ud af memory-familien"

    fn = dict(_MEMORY_UNCONDITIONAL)["associative_recall"]
    assert fn is _mem_associative_recall_live

    family = _REGISTRY.get("cluster_memory") or {}
    assert family.get("default_enabled") is True, (
        "familien der nu bærer associativ recall er slukket — evnen ville være død"
    )
    assert family.get("default_cadence_minutes") == 2, (
        "kadencen skal matche den pensionerede daemons 2 minutter"
    )


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


# ── `_safe_surface` havde TO udfald hvor der er tre (25/9-2026) ─────────────


def test_en_flade_der_bygger_staar_som_den_selv_siger():
    from core.services.heartbeat_runtime import _safe_surface

    ud: dict = {}
    _safe_surface(ud, "en_flade", lambda: {"active": True, "summary": "noget"})
    assert ud["en_flade"] == {"active": True, "summary": "noget"}


def test_en_flade_der_KASTER_meldes_som_fejlet():
    from core.services.heartbeat_runtime import _safe_surface

    def _knaek():
        raise RuntimeError("tabellen er væk")

    ud: dict = {}
    _safe_surface(ud, "en_flade", _knaek)
    assert ud["en_flade"]["active"] is False
    assert ud["en_flade"]["error"] == "surface-build-failed"
    assert ud["en_flade"]["summary"], "en fejl skal kunne læses, ikke kun tælles"


def test_en_PER_BRUGER_flade_uden_bruger_er_hverken_doed_eller_tom():
    """Fem flader er per bruger og kaster `NoUserContextError` når en kalder
    uden bruger spørger.

    Målt 25/9-2026: set fra `/mc/runtime` med et system-token meldte
    `day_shape_memory`, `memory_write_policy`, `cross_session_threads`,
    `relation_dynamics` og `relational_warmth` sig døde med TOM summary; set
    fra Bjørns app, som spørger som ham, stod de med rigtige tal. Samme flade,
    to svar, og det ene løj.

    «Ikke relevant for denne kalder» er et tredje udfald.
    """
    from core.runtime.workspace_paths import NoUserContextError
    from core.services.heartbeat_runtime import _safe_surface

    def _uden_bruger():
        raise NoUserContextError("workspace_dir() called without user_id")

    ud: dict = {}
    _safe_surface(ud, "en_flade", _uden_bruger)

    assert ud["en_flade"]["active"] is True, "modulet lever — kalderen har bare ingen bruger"
    assert ud["en_flade"]["scope"] == "per-bruger"
    assert "brugerkontekst" in ud["en_flade"]["summary"]
    assert "error" not in ud["en_flade"]


def test_centralen_faar_KASTEDE_flader_ikke_bare_tomme(monkeypatch):
    """`failed` betød «active er False» og ikke «byggeren kastede».

    Enhver ærligt tom flade meldte sig derfor som en FEJL til Centralen — og
    de var mange: 13 af 71 stod `active: false` samme dag, og de fleste af dem
    kørte fint.
    """
    import core.services.heartbeat_runtime as HR

    observeret: list[dict] = []

    class _Falsk:
        def observe(self, payload):
            observeret.append(payload)

    monkeypatch.setattr("core.services.central_core.central", lambda: _Falsk())
    monkeypatch.setattr(HR, "_SURFACE_OBSERVE_AT", {})

    # Ærligt tom, men kørende: må IKKE meldes som fejl.
    _ud: dict = {}
    HR._safe_surface(_ud, "tom_men_levende",
                     lambda: {"active": False, "summary": "ingenting endnu"})

    assert observeret, "der blev ikke observeret noget"
    assert observeret[-1]["active"] is True, (
        "en ærligt tom flade blev meldt som en fejl til Centralen"
    )
    assert observeret[-1]["error"] is None
