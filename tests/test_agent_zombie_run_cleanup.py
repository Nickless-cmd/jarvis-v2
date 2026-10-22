"""Et terminalt assignment maa ikke efterlade et run i waiting_for_approval.

Maalt 22/10-2026 i den levende DB: `asg-4bea67d6cc004dd4` var `cancelled`,
agenten var `cancelled`, checkpointet var `discarded` — og runnet stod stadig
`waiting_for_approval` med `finished_at` sat. Det er samme zombie som
`agent_parking.py` beskriver for sin vej, men ad denne vej blev checkpointet
discarded uden at run-raekken blev lukket.

Fordi `decided_parked()` kun ser checkpoints der ER `parked`, faldt raekken ud
af oprydningen og blev aldrig samlet op: den holdt kortet i «venter» for evigt.
"""
from __future__ import annotations


def test_terminalt_udfald_lukker_ventende_run(isolated_runtime):
    import core.runtime.db_agent_contract as c
    from core.runtime.db_agent_runtime import _ensure_agent_runtime_tables

    conn = c.connect()
    c.ensure_agent_contract_tables(conn)
    _ensure_agent_runtime_tables(conn)

    nu = "2026-10-22T12:00:00+00:00"
    conn.execute(
        "INSERT INTO agent_assignments (assignment_id, agent_id, owner_user_id, "
        "origin_session_id, goal, status, created_at, updated_at) VALUES (?,?,?,?,?,?,?,?)",
        ("asg-zombie", "agent-zombie", "owner", "sess", "goal", "active", nu, nu))
    conn.execute(
        "INSERT INTO agent_runs (run_id, agent_id, status, created_at, updated_at, assignment_id) "
        "VALUES (?,?,?,?,?,?)",
        ("run-zombie", "agent-zombie", "waiting_for_approval", nu, nu, "asg-zombie"))
    conn.commit()

    c.commit_terminal_outcome(assignment_id="asg-zombie", status="cancelled")

    row = conn.execute("SELECT status, finished_at FROM agent_runs WHERE run_id='run-zombie'").fetchone()
    assert row["status"] == "cancelled", (
        "runnet blev efterladt i waiting_for_approval efter et terminalt assignment")
    assert row["finished_at"], "lukket run skal have et finished_at"


def test_et_korende_run_roeres_ikke(isolated_runtime):
    """Kun waiting_for_approval lukkes — et run der faktisk koerer skal staa urørt."""
    import core.runtime.db_agent_contract as c
    from core.runtime.db_agent_runtime import _ensure_agent_runtime_tables

    conn = c.connect()
    c.ensure_agent_contract_tables(conn)
    _ensure_agent_runtime_tables(conn)

    nu = "2026-10-22T12:00:00+00:00"
    conn.execute(
        "INSERT INTO agent_assignments (assignment_id, agent_id, owner_user_id, "
        "origin_session_id, goal, status, created_at, updated_at) VALUES (?,?,?,?,?,?,?,?)",
        ("asg-live", "agent-live", "owner", "sess", "goal", "active", nu, nu))
    conn.execute(
        "INSERT INTO agent_runs (run_id, agent_id, status, created_at, updated_at, assignment_id) "
        "VALUES (?,?,?,?,?,?)",
        ("run-live", "agent-live", "running", nu, nu, "asg-live"))
    conn.commit()

    c.commit_terminal_outcome(assignment_id="asg-live", status="completed")

    row = conn.execute("SELECT status FROM agent_runs WHERE run_id='run-live'").fetchone()
    assert row["status"] == "running"
