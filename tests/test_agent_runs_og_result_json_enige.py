"""`agent_runs` og `result.json` skal være enige om samme kørsels terminale status.

MÅLT 23/11-2026, `run-6380f18859a141ab`:

    agent_runs   failed     CLI_BACKEND_FAILED  execution
    result.json  cancelled  CANCELLED           recovery

Rod: to uafhængige skrivestier. Annullering kalder `settle_agent_status`, som
skriver `result.json` + assignmentets (uforanderlige) udfald — på et tidspunkt
hvor run-rækken endnu ikke bærer nogen kode. Workerens exception-handler
skriver BAGEFTER `update_agent_run(status="failed", CLI_BACKEND_FAILED)`; dens
`settle` afvises, fordi assignmentet allerede er terminalt. Rækken ender på den
sidste fejl, artefakten på den første lukning.

Valgt retning: assignmentets terminale udfald (= `result.json`) er eneste
terminale sandhed; en sen terminal skrivning til et run under et allerede
terminalt assignment afledes fra det. Den observerede årsag bevares i
`failure_reason`.
"""

from __future__ import annotations

import json


def _setup(isolated_runtime):
    import core.runtime.db_agent_contract as c
    from core.runtime.db_agent_artifacts import ensure_artifact_tables
    from core.runtime.db_agent_runtime import _ensure_agent_runtime_tables

    conn = c.connect()
    c.ensure_agent_contract_tables(conn)
    _ensure_agent_runtime_tables(conn)
    ensure_artifact_tables(conn)
    nu = "2026-11-23T13:02:51+00:00"
    conn.execute(
        "INSERT INTO agent_assignments (assignment_id, agent_id, owner_user_id, "
        "origin_session_id, goal, status, created_at, updated_at) VALUES (?,?,?,?,?,?,?,?)",
        ("asg-div", "agent-div", "owner", "sess", "goal", "active", nu, nu))
    conn.execute(
        "INSERT INTO agent_registry (agent_id, status, role, goal, provider, model, "
        "persistent, last_error, created_at, updated_at) VALUES (?,?,?,?,?,?,?,?,?,?)",
        ("agent-div", "active", "executor", "goal", "claude-cli", "sonnet", 0, "", nu, nu))
    conn.execute(
        "INSERT INTO agent_runs (run_id, agent_id, status, created_at, updated_at, "
        "assignment_id, attempt_no, error_code, error_phase) VALUES (?,?,?,?,?,?,?,?,?)",
        ("run-div", "agent-div", "active", nu, nu, "asg-div", 1, "", ""))
    conn.commit()
    return c, conn


def test_backend_fejl_efter_annullering_giver_samme_sandhed(isolated_runtime):
    from core.runtime.db_agent_artifacts import get_artifact_record
    from core.runtime.db_agent_runtime import get_agent_run, update_agent_run

    c, conn = _setup(isolated_runtime)

    # 1) annullering lukker assignmentet og skriver result.json — runnet har endnu ingen kode
    c.settle_agent_status(agent_id="agent-div", registry_status="cancelled")
    # 2) workerens exception-handler lander bagefter med backend-fejlen
    update_agent_run(
        "run-div", status="failed", finished_at="2026-11-23T13:04:54+00:00",
        failure_reason="CLI backend fejlede", error_code="CLI_BACKEND_FAILED",
        error_phase="execution")

    rec = get_artifact_record(run_id="run-div", name="result.json")
    assert rec, "result.json blev ikke skrevet"
    with open(rec["path"], encoding="utf-8") as f:
        art = json.load(f)
    run = get_agent_run("run-div")

    assert (run["status"], run["error_code"], run["error_phase"]) == (
        art["status"], art["error_code"], art["error_phase"]), (
        f"divergens: agent_runs={run['status']}/{run['error_code']}/{run['error_phase']} "
        f"result.json={art['status']}/{art['error_code']}/{art['error_phase']}")
    out = json.loads(conn.execute(
        "SELECT outcome_json FROM agent_assignments WHERE assignment_id='asg-div'"
    ).fetchone()["outcome_json"])
    assert out["status"] == art["status"] and out["error_code"] == art["error_code"]
    assert "CLI backend fejlede" in str(run["failure_reason"]), "observeret aarsag skal bevares"


def test_run_uden_terminalt_assignment_roeres_ikke(isolated_runtime):
    """Vagten må ikke omskrive almindelige fejl."""
    from core.runtime.db_agent_runtime import get_agent_run, update_agent_run

    _setup(isolated_runtime)
    update_agent_run("run-div", status="failed", error_code="CLI_BACKEND_FAILED",
                     error_phase="execution")
    run = get_agent_run("run-div")
    assert (run["status"], run["error_code"], run["error_phase"]) == (
        "failed", "CLI_BACKEND_FAILED", "execution")
