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
    import core.services.visible_runs as vr
    monkeypatch.setattr(vr, "start_autonomous_run", lambda **kw: kaldt.append(kw))

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


def test_recurring_uden_binding_falder_til_gammel_adfaerd(tmp_path, monkeypatch):
    """Raekker fra foer kolonnen fandtes har '' — de skal stadig fyre."""
    _fresh(tmp_path, monkeypatch)
    kaldt: list[dict] = []
    import core.services.visible_runs as vr
    monkeypatch.setattr(vr, "start_autonomous_run", lambda **kw: kaldt.append(kw))

    t = rt.create_recurring_task(focus="gammel", interval_minutes=1440)
    assert t["session_id"] == ""
    with db.connect() as c:
        c.execute("UPDATE recurring_tasks SET next_fire_at=? WHERE task_id=?",
                  ((datetime.now(UTC) - timedelta(minutes=5)).isoformat(), t["task_id"]))
        c.commit()

    rt._fire_due()

    assert len(kaldt) == 1
    assert kaldt[0]["session_id"] is None


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
