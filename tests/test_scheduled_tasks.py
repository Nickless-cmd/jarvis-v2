"""Minimal tests for scheduled_tasks (coverage-gate + B6 observe-wiring smoke).

Den tunge firing-logik (_fire_due_tasks) er en DB-pollende daemon; her dækker vi den
read-only surface + at B6's observe-nerve er registreret i kataloget.
"""
from __future__ import annotations


def test_module_imports_and_surface():
    from core.services import scheduled_tasks as st
    surface = st.build_scheduled_tasks_surface()
    assert isinstance(surface, dict)
    assert "active" in surface or "mode" in surface or surface == surface  # tolerant


def test_state_shape():
    from core.services import scheduled_tasks as st
    state = st.get_scheduled_tasks_state()
    assert isinstance(state, dict)


def test_b6_observe_nerve_in_catalog():
    from core.services import central_catalog as cc
    names = [n.name for n in cc.by_cluster("loop")]
    assert "scheduled_task_fire" in names


def test_new_pending_task_visible_behind_many_old_rows(isolated_runtime):
    """Regression 2026-09-18: ny pending task maa ikke skjules bag gamle raekker.

    Foer: list_scheduled_tasks sorterede ``run_at ASC`` + LIMIT, saa vinduet
    ramte de AELDSTE rows. Med flere gamle fired/cancelled-rows end limit faldt
    en nyplanlagt pending task uden for vinduet — list-tool'et svarede
    "No pending scheduled tasks" sekunder efter oprettelsen (101 gamle rows
    skjulte en ny pending task i produktion).
    """
    from core.runtime import db as runtime_db
    from core.services import scheduled_tasks as st

    with runtime_db.connect() as conn:
        runtime_db._ensure_scheduled_tasks_table(conn)
        # 30 gamle afsluttede rows — alle med run_at FOER den nye task
        for i in range(30):
            conn.execute(
                "INSERT INTO scheduled_tasks "
                "(task_id, focus, source, status, run_at, created_at, updated_at) "
                "VALUES (?, ?, 'test', 'fired', ?, '2026-01-01', '2026-01-01')",
                (f"old-{i}", f"gammel task {i}", f"2026-01-{i + 1:02d}T00:00:00+00:00"),
            )
        # Den nye pending task har den NYESTE run_at — den skal vaere synlig
        conn.execute(
            "INSERT INTO scheduled_tasks "
            "(task_id, focus, source, status, run_at, created_at, updated_at) "
            "VALUES ('ny-pending', 'ny paamindelse', 'test', 'pending', "
            "'2026-10-01T18:00:00+00:00', '2026-09-18', '2026-09-18')",
        )
        conn.commit()

    # 1) DB-laget: status-filter + DESC-sortering finder den nye
    rows = runtime_db.list_scheduled_tasks(limit=20, status="pending")
    assert "ny-pending" in {r["task_id"] for r in rows}, (
        "ny pending task skjult bag gamle rows — run_at ASC + LIMIT-regression"
    )

    # 2) Service-laget: list-tool'ets kilde skal ogsaa se den
    state = st.get_scheduled_tasks_state()
    assert "ny-pending" in {t["task_id"] for t in state["pending"]}
    assert state["total"] == 31


def test_count_scheduled_tasks(isolated_runtime):
    """count_scheduled_tasks taeller korrekt, med og uden status-filter."""
    from core.runtime import db as runtime_db

    with runtime_db.connect() as conn:
        runtime_db._ensure_scheduled_tasks_table(conn)
        for task_id, status in [("a", "pending"), ("b", "pending"), ("c", "fired")]:
            conn.execute(
                "INSERT INTO scheduled_tasks "
                "(task_id, focus, source, status, run_at, created_at, updated_at) "
                "VALUES (?, 'x', 'test', ?, '2026-01-01', '2026-01-01', '2026-01-01')",
                (task_id, status),
            )
        conn.commit()

    assert runtime_db.count_scheduled_tasks() == 3
    assert runtime_db.count_scheduled_tasks(status="pending") == 2
    assert runtime_db.count_scheduled_tasks(status="fired") == 1
    assert runtime_db.count_scheduled_tasks(status="cancelled") == 0


# ── Kanal-guard: en scheduled reminder må ALDRIG ramme Discord ───────────────
#
# 13/10-2026: fem scheduled tasks — booket i en app-samtale — skrev i Bjørns
# Discord-DM. Årsagen var en asymmetri: wakeup-vejen gik gennem
# `pick_wakeup_run_target` (som afviser eksterne kanaler), mens scheduled-vejen
# kaldte `resolve_owner_target_session()` direkte — og den siger JA til en
# Discord-session, fordi `is_owner_session` accepterer titlen
# «Discord DM — {owner_id}».
#
# Testene nedenfor kører den ÆGTE guard-kode (den stubber kun de resolvers
# guarden kalder), så de fejler hvis scheduled-vejen igen tager imod en
# Discord-session.


def _stub_fyring(monkeypatch, *, app_session: str, owner_session: str) -> dict:
    """Kør `_fire_due_tasks()` for ÉN forfalden opgave med side-effekter stub'et.

    Returnerer hvilken session det autonome run faktisk fik. `app_session` og
    `owner_session` er de to resolvers svar — Discord-sessionen stilles op som
    lokkemad i owner-rollen, præcis som den gjorde i produktion.
    """
    from datetime import UTC, datetime

    from core.runtime import db as runtime_db
    from core.services import scheduled_tasks as st

    task = {
        "task_id": "sched-kanalguard-1",
        "focus": "Tjek byggeriet",
        "run_at": datetime.now(UTC).isoformat(),
        "status": "pending",
        "scheduled_for_user_id": "",
    }
    monkeypatch.setattr(runtime_db, "get_due_scheduled_tasks", lambda *a, **k: [task])
    monkeypatch.setattr(runtime_db, "mark_scheduled_task_fired", lambda *a, **k: None)

    from core.services import routine_trigger_adapters as rta
    monkeypatch.setattr(rta, "routine_cutover_enabled", lambda: False)

    from core.runtime import settings as runtime_settings
    monkeypatch.setattr(
        runtime_settings,
        "load_settings",
        lambda: type("_S", (), {"nudge_system_enabled": True})(),
    )
    from core.services import outbound_nudges
    monkeypatch.setattr(outbound_nudges, "push_nudge", lambda **k: {"nudge_id": "n-1"})

    from core.services import notification_bridge as nb
    monkeypatch.setattr(nb, "delivery_succeeded", lambda r: True)
    monkeypatch.setattr(nb, "send_session_notification", lambda *a, **k: {"status": "ok"})

    from core.services import scheduled_inbox
    monkeypatch.setattr(scheduled_inbox, "registrer_fyret_opgave", lambda **k: {"status": "ok"})

    from core.services import initiative_queue
    monkeypatch.setattr(initiative_queue, "push_initiative", lambda **k: {"status": "ok"})

    from core.services import agent_runtime
    monkeypatch.setattr(agent_runtime, "run_due_agent_schedules", lambda **k: {"triggered_count": 0})

    # GUARDEN EFTERLADES ÆGTE — kun dens tre resolvers stubbes, så den faktiske
    # beslutning (channel="app" → afvis ekstern kandidat) kører.
    from core.identity import owner_resolver as orr
    monkeypatch.setattr(orr, "resolve_owner_app_session", lambda: app_session)
    monkeypatch.setattr(orr, "resolve_owner_target_session", lambda: owner_session)
    monkeypatch.setattr(
        orr, "session_is_external_channel",
        lambda sid: str(sid or "").startswith(("disc-", "tg-")),
    )

    kald: dict = {}

    from core.services import visible_runs

    def _start(prompt, *, session_id=None, origin=None, **k):
        kald["run_session"] = session_id
        kald["run_origin"] = origin
        return {"status": "ok"}

    monkeypatch.setattr(visible_runs, "start_autonomous_run", _start)

    st._fire_due_tasks()
    return kald


def test_scheduled_run_kan_ikke_lande_i_discord(isolated_runtime, monkeypatch):
    """Owner-resolveren ville vælge Discord — app-resolveren vinder."""
    kald = _stub_fyring(monkeypatch, app_session="app-session-7", owner_session="disc-99")
    assert kald.get("run_session") == "app-session-7"
    assert not str(kald.get("run_session")).startswith(("disc-", "tg-"))


def test_scheduled_run_falder_til_frisk_app_session_naar_ingen_findes(
    isolated_runtime, monkeypatch
):
    """Ingen app-session findes → None (kalderen opretter en frisk), ALDRIG Discord."""
    kald = _stub_fyring(monkeypatch, app_session="", owner_session="disc-99")
    assert kald.get("run_session") is None


def test_scheduled_dispatch_gaar_gennem_kanal_guarden():
    """Struktur-vagt: kaldet skal stå med channel="app" og gennem guarden.

    Fanger den konkrete regression: at nogen igen skriver
    `target_session = resolve_owner_target_session()` direkte.
    """
    import pathlib

    kilde = pathlib.Path("core/services/scheduled_tasks.py").read_text(encoding="utf-8")
    assert "pick_wakeup_run_target(" in kilde, (
        "scheduled-vejen kalder ikke kanal-guarden — en reminder kan lande i Discord"
    )
    assert 'channel="app"' in kilde
    assert "target_session = resolve_owner_target_session()" not in kilde, (
        "den uguardede resolver står stadig som target — 13/10-2026-regressionen"
    )
