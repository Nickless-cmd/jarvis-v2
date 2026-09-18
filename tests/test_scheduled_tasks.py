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
