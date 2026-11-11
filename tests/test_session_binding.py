"""Session-bindingen: hvert ur skal bære den samtale jobbet blev bestilt i.

Målt 14/10-2026 (Bjørn: «tingene skal vække den aktive session de er bestilt
i»): recurring, scheduled og heartbeat startede alle et run i en
`auto-{origin}-{dato}`-silo, fordi ingen af tabellerne bar samtalen. 367
recurring-runs skrev deres svar i en session ingen læser.

Disse tests pinner bindingen i DATAMODELLEN — den kan ikke gættes bagefter,
den skal skrives ned da jobbet blev bestilt.
"""
from datetime import UTC, datetime, timedelta

import core.runtime.db as db
import core.runtime.db_core as db_core
import core.services.recurring_tasks as rt
from core.identity.workspace_context import reset_context, set_context


def _fresh(tmp_path, monkeypatch):
    monkeypatch.setattr(db_core, "DB_PATH", tmp_path / "t.db")
    monkeypatch.setenv("JARVIS_HOME", str(tmp_path))
    db.init_db()
    rt._ensure_table()
    # ÉN VÆKKER (11/11-2026): recurring-vejen afleverer nu til indbakken, så
    # `inbox_items` skal findes i temp-DB'en. `db_inbox._ensure_skema` kører
    # DDL ÉN gang pr. PROCESSUS, så uden dette nulstilles flaget aldrig og den
    # anden temp-DB får ingen tabel — testen fejler med «no such table».
    import core.runtime.db_inbox as db_inbox
    monkeypatch.setattr(db_inbox, "_skema_klar", False)
    db_inbox._ensure_skema(db.connect())


# ── Den fælles binder ───────────────────────────────────────────────────────

def test_bind_session_grundadfaerd():
    from core.services.session_binding import bind_session

    assert bind_session("chat-1") == "chat-1"
    assert bind_session("  chat-2  ") == "chat-2"
    # En autonom silo er ikke en samtale — den må aldrig bindes.
    assert bind_session("auto-recurring-20261014") == ""
    assert bind_session("auto-dream-20261014") == ""
    # Ingen kontekst og ingen eksplicit → tom, ikke en gaet.
    assert bind_session("") == ""


def test_bind_session_laeser_den_aktive_kontekst():
    from core.services.session_binding import bind_session

    tok = set_context(workspace_name="bjorn", session_id="chat-ctx-9")
    try:
        assert bind_session() == "chat-ctx-9"
        # Eksplicit vinder over konteksten.
        assert bind_session("chat-eksplicit") == "chat-eksplicit"
    finally:
        reset_context(tok)


# ── Ur 1: recurring ─────────────────────────────────────────────────────────

def test_recurring_binder_kontekstens_samtale(tmp_path, monkeypatch):
    _fresh(tmp_path, monkeypatch)
    tok = set_context(workspace_name="bjorn", session_id="chat-ctx-rec")
    try:
        t = rt.create_recurring_task(focus="morgenbrief", interval_minutes=1440)
    finally:
        reset_context(tok)
    assert t["session_id"] == "chat-ctx-rec"
    with db.connect() as c:
        gemt = c.execute("SELECT session_id FROM recurring_tasks WHERE task_id=?",
                         (t["task_id"],)).fetchone()[0]
    assert gemt == "chat-ctx-rec"


def test_recurring_binder_ALDRIG_en_auto_silo(tmp_path, monkeypatch):
    """Et autonomt run der opretter en opgave må ikke binde den til sin egen silo."""
    _fresh(tmp_path, monkeypatch)
    tok = set_context(workspace_name="bjorn", session_id="auto-recurring-20261014")
    try:
        t = rt.create_recurring_task(focus="x", interval_minutes=60)
    finally:
        reset_context(tok)
    assert t["session_id"] == ""


def test_recurring_fyrer_i_den_bundne_samtale(tmp_path, monkeypatch):
    """Kernen i fixet: runnet lander i samtalen, ikke i auto-recurring."""
    _fresh(tmp_path, monkeypatch)
    kaldt: list[dict] = []
    # ÉN VÆKKER (11/11-2026): recurring starter ikke længere et run selv — den
    # afleverer til indbakken med samtalen bundet på posten. Spionen skal derfor
    # ramme gatewayen; ellers ser den nul kald og testen bliver grøn af den
    # forkerte grund.
    import core.services.wake_gateway as wg
    monkeypatch.setattr(
        wg, "anmod_om_vaekning",
        lambda **kw: kaldt.append(kw) or {"status": "queued"},
    )

    t = rt.create_recurring_task(focus="medicin", interval_minutes=1440,
                                 session_id="chat-bundet-1")
    with db.connect() as c:
        c.execute("UPDATE recurring_tasks SET next_fire_at=? WHERE task_id=?",
                  ((datetime.now(UTC) - timedelta(minutes=5)).isoformat(), t["task_id"]))
        c.commit()

    rt._fire_due()

    assert len(kaldt) == 1, "opgaven fyrede ikke"
    assert kaldt[0]["session_id"] == "chat-bundet-1"
    assert kaldt[0]["origin"] == "recurring"
    assert kaldt[0]["tekst"] == "medicin"
    # Dedup-nøglen skal være FOREKOMSTEN — kun task_id ville dedupes mod den
    # første post for evigt, så en daglig opgave kun kunne vække én gang.
    assert kaldt[0]["sag"].startswith(f"recurring:{t['task_id']}:")
    assert kaldt[0]["sag"] != f"recurring:{t['task_id']}:"


def test_recurring_uden_binding_falder_til_gammel_adfaerd(tmp_path, monkeypatch):
    """Raekker fra foer kolonnen fandtes har '' — de skal stadig fyre."""
    _fresh(tmp_path, monkeypatch)
    kaldt: list[dict] = []
    import core.services.wake_gateway as wg
    monkeypatch.setattr(
        wg, "anmod_om_vaekning",
        lambda **kw: kaldt.append(kw) or {"status": "queued"},
    )

    t = rt.create_recurring_task(focus="gammel", interval_minutes=1440)
    assert t["session_id"] == ""
    with db.connect() as c:
        c.execute("UPDATE recurring_tasks SET next_fire_at=? WHERE task_id=?",
                  ((datetime.now(UTC) - timedelta(minutes=5)).isoformat(), t["task_id"]))
        c.commit()

    rt._fire_due()

    assert len(kaldt) == 1
    # Uden binding normaliserer kilden til "" — den tomme adresse betyder
    # «slå den aktive op nu», ikke «ingen adresse».
    assert kaldt[0]["session_id"] == ""


# ── Ur 2: scheduled ─────────────────────────────────────────────────────────

def test_scheduled_baerer_samtalen(tmp_path, monkeypatch):
    _fresh(tmp_path, monkeypatch)
    from core.runtime.db import get_scheduled_task
    from core.services.scheduled_tasks import push_scheduled_task

    t = push_scheduled_task(focus="tjek noget", delay_minutes=5, session_id="chat-sched-1")
    assert t["session_id"] == "chat-sched-1"
    row = get_scheduled_task(t["task_id"])
    assert row["session_id"] == "chat-sched-1"


# ── Ur 3: heartbeat gennem initiativ-koeen ──────────────────────────────────

def test_initiativ_baerer_samtalen(tmp_path, monkeypatch):
    """Scheduled → initiativ → heartbeat: uden dette led tabes samtalen."""
    _fresh(tmp_path, monkeypatch)
    from core.runtime.db import get_runtime_initiative
    from core.services.initiative_queue import push_initiative

    iid = push_initiative(focus="foelg op paa noget konkret", session_id="chat-init-1")
    assert iid, "initiativet blev afvist af kvalitetsporten"
    row = get_runtime_initiative(iid)
    assert row["session_id"] == "chat-init-1"


def test_heartbeat_sender_samtalen_videre(monkeypatch):
    from core.services import routine_trigger_adapters as rta
    import core.services.visible_runs as vr

    kaldt: list[dict] = []
    monkeypatch.setattr(vr, "start_autonomous_run", lambda *a, **kw: kaldt.append(kw))
    # Kør legacy-grenen direkte — det er den der starter runnet.
    monkeypatch.setattr(
        rta, "dispatch_system",
        lambda producer, sid, *, trigger_inputs, legacy, adapters=None: (legacy(), None)[1],
    )

    rta.dispatch_heartbeat_initiative(focus="f", initiative_id="i", session_id="chat-hb-1")

    assert kaldt[0]["session_id"] == "chat-hb-1"
    assert kaldt[0]["origin"] == "heartbeat"


def test_heartbeat_uden_samtale_er_systemets_eget(monkeypatch):
    from core.services import routine_trigger_adapters as rta
    import core.services.visible_runs as vr

    kaldt: list[dict] = []
    monkeypatch.setattr(vr, "start_autonomous_run", lambda *a, **kw: kaldt.append(kw))
    monkeypatch.setattr(
        rta, "dispatch_system",
        lambda producer, sid, *, trigger_inputs, legacy, adapters=None: (legacy(), None)[1],
    )

    rta.dispatch_heartbeat_initiative(focus="f", initiative_id="i")

    assert kaldt[0]["session_id"] is None


def test_heartbeat_afvisning_parkeres_i_stedet_for_at_forsvinde(monkeypatch):
    """Et False fra run-starteren er en afvisning, ikke en levering."""
    from core.services import routine_trigger_adapters as rta
    import core.services.run_guard as run_guard
    import core.services.visible_runs as vr

    parkeret: list[dict] = []
    monkeypatch.setattr(vr, "start_autonomous_run", lambda *_a, **_kw: False)
    monkeypatch.setattr(
        rta, "dispatch_system",
        lambda _producer, _sid, *, trigger_inputs, legacy, adapters=None: (
            legacy(), None
        )[1],
    )
    monkeypatch.setattr(
        run_guard,
        "parker_forpligtelse",
        lambda **kwargs: parkeret.append(kwargs) or {"status": "ok"},
    )

    result = rta.dispatch_heartbeat_initiative(
        focus="undersoeg den konkrete driftstilstand",
        initiative_id="init-fbcc10cadd",
        session_id="auto-heartbeat-20261101",
    )

    assert result == {"status": "ok"}
    assert parkeret == [{
        "origin": "heartbeat",
        "session_id": "auto-heartbeat-20261101",
        "beskrivelse": "undersoeg den konkrete driftstilstand",
        "kilde_id": "afvist-heartbeat-init-fbcc10cadd",
    }]
