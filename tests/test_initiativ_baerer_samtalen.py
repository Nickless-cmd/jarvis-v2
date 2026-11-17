"""Initiativet skal bære den SAMTALE det kom fra (17/11-2026).

## Hvorfor denne fil findes

Målt 17/11-2026: `runtime_initiatives.session_id` var udfyldt i **0 af 5.865**
rækker. Hele læse-vejen var intakt — kolonnen findes, INSERT'en skriver den,
`list_runtime_initiatives` returnerer feltet, og
`dispatch_heartbeat_initiative` sender det videre til
`start_autonomous_run(session_id=...)`, som lader en eksplicit session vinde
over `auto-{origin}-{dato}`-siloen. Der var bare **ingen der skrev en værdi**.

Konsekvensen var målt i drift: et initiativ født i en samtale blev aktet ind i
`auto-heartbeat-YYYYMMDD`, og arbejdet vendte aldrig tilbage til den samtale
der bestilte det. `scheduled_tasks.session_id` er udfyldt i 58 af 179 rækker —
de kendte altså deres samtale og smed den væk i `push_initiative`-kaldet.

Testen her måler ikke at parameteren findes. Den måler at værdien lander i
databasen, og at silo-reglen i `session_binding.bind_session` stadig holder:
en `auto-*`-session må ALDRIG bindes, for så arver siloen sig selv.
"""

from __future__ import annotations


def _session_for(initiative_id: str) -> str:
    from core.runtime import db_core

    with db_core.connect() as conn:
        row = conn.execute(
            "SELECT session_id FROM runtime_initiatives WHERE initiative_id = ?",
            (initiative_id,),
        ).fetchone()
    assert row is not None, f"initiativet {initiative_id} blev ikke oprettet"
    return str(row[0] or "")


def test_vaerktoejet_baerer_samtalen_ind_i_koeen(isolated_runtime):
    """`push_initiative` kaldt som værktøj skal gemme `_runtime_session_id`."""
    from core.tools.simple_tools_native import _exec_push_initiative

    r = _exec_push_initiative({
        "focus": "Følg op på readback-feltet",
        "_runtime_session_id": "chat-5f65563201be4a1",
    })

    assert r.get("status") == "ok", r
    assert _session_for(str(r["initiative_id"])) == "chat-5f65563201be4a1"


def test_uden_samtale_bindes_intet(isolated_runtime):
    """En daemon har ingen samtale — så skal feltet være tomt, ikke gættet."""
    from core.tools.simple_tools_native import _exec_push_initiative

    r = _exec_push_initiative({"focus": "Noget den indre stemme rejste"})

    assert r.get("status") == "ok", r
    assert _session_for(str(r["initiative_id"])) == ""


def test_en_silo_arver_aldrig_sig_selv(isolated_runtime):
    """`auto-*` må ikke bindes — ellers genskabes præcis det problem bindingen fjerner.

    Reglen bor i `session_binding.bind_session` og gælder ALLE kilder, også en
    der (fejlagtigt) sender en silo videre.
    """
    from core.services.initiative_queue import push_initiative

    iid = push_initiative(
        focus="Skal ikke bindes til siloen",
        source="scheduled-task",
        session_id="auto-heartbeat-20261117",
    )

    assert _session_for(iid) == ""


def test_en_rigtig_samtale_bindes(isolated_runtime):
    """Den ægte kobling: scheduled-task'ens samtale følger med hele vejen."""
    from core.services.initiative_queue import push_initiative

    iid = push_initiative(
        focus="Påmindelse bestilt i en samtale",
        source="scheduled-task",
        source_id="task-123",
        session_id="chat-9ab77c10de4f2",
    )

    assert _session_for(iid) == "chat-9ab77c10de4f2"


def test_den_rigtige_fyr_sti_baerer_samtalen(isolated_runtime):
    """`_fire_due_tasks` — ikke bare `push_initiative` — skal bære samtalen.

    Målt 17/11-2026: kæden var intakt i koden (`task_session` læses fra
    `scheduled_tasks.session_id` og sendes til `push_initiative`), men
    `runtime_initiatives.session_id` var udfyldt i 1 af 5.871 rækker — og den
    ene var en test. Ingen havde målt den VEJ der faktisk fyrer.

    Testen indsætter en forfalden task med en samtale og kalder den ægte
    `_fire_due_tasks`. Den fejler hvis nogen fjerner `session_id=task_session`
    fra dispatch-kaldet, eller hvis fyr-stien en dag tager en anden gren.
    """
    from datetime import datetime, timedelta, timezone

    from core.runtime import db as runtime_db
    from core.services import scheduled_tasks as st

    session = "chat-1fa646106874479db4c6c4b8b8868f59"
    task_id = "sched-baerer-samtalen"
    foraldret = (datetime.now(timezone.utc) - timedelta(minutes=5)).isoformat()

    with runtime_db.connect() as conn:
        runtime_db._ensure_scheduled_tasks_table(conn)
        conn.execute(
            "INSERT INTO scheduled_tasks "
            "(task_id, focus, source, status, run_at, created_at, updated_at, session_id) "
            "VALUES (?, ?, 'jarvis-tool', 'pending', ?, ?, ?, ?)",
            (task_id, "Følg op på kalibreringen", foraldret, foraldret, foraldret, session),
        )
        conn.commit()

    st._fire_due_tasks()

    from core.runtime import db_core

    with db_core.connect() as conn:
        row = conn.execute(
            "SELECT session_id FROM runtime_initiatives WHERE source_id = ?",
            (task_id,),
        ).fetchone()

    assert row is not None, "fyr-stien oprettede intet initiativ for den forfaldne task"
    assert str(row[0] or "") == session, (
        f"initiativet mistede samtalen: fik {row[0]!r}, ventede {session!r}"
    )
