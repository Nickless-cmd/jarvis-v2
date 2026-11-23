"""`declined` skal være TERMINAL — og baeres hele vejen ud til foraelderen.

MAALT 23/11-2026 i den levende base:

    run_status  kode            asg_status
    declined    AGENT_DECLINED  completed

Barnet havde selv meldt «jeg kunne ikke levere». Runnet bar det korrekt
(`status=declined`, `error_code=AGENT_DECLINED`) — men ASSIGNMENTET, som er
det lag foraelderen laeser, stod `completed`. Signalet doede praecis paa
overgangen mellem de to raekker.

To aarsager, én rod:

1. `declined` var ikke i `ASSIGNMENT_TERMINAL`, saa
   `commit_terminal_outcome(status="declined")` blev afvist med
   INVALID_TRANSITION. Den eneste vej tilbage var at kalde udfaldet
   `completed` — altsaa at lyve om det.
2. `target` kom udelukkende fra `_SETTLING[registry_status]`, og
   registry-status er `completed` fordi agenten svarede. Barnets egen dom
   naaede aldrig udfaldet.

Testene her holder fire ting fast: at status er terminal, at den kan
committes og baeres i outbox-payloaden, at den AEgte vej (settle) loefter
runnets dom op i assignmentet — og at en rigtig leverance stadig bliver
`completed`, saa vagten ikke goer alt til `declined`.
"""

from __future__ import annotations


def _contract_db():
    """En frisk contract-base med de to tabeller vejen kraever."""
    import core.runtime.db_agent_contract as c
    from core.runtime.db_agent_runtime import _ensure_agent_runtime_tables

    conn = c.connect()
    c.ensure_agent_contract_tables(conn)
    _ensure_agent_runtime_tables(conn)
    return c, conn


def _indsæt_assignment(conn, *, asg="asg-decl", agent="agent-decl", status="active"):
    nu = "2026-11-23T10:00:00+00:00"
    conn.execute(
        "INSERT INTO agent_assignments (assignment_id, agent_id, owner_user_id, "
        "origin_session_id, goal, status, created_at, updated_at) VALUES (?,?,?,?,?,?,?,?)",
        (asg, agent, "owner", "sess", "goal", status, nu, nu))
    conn.commit()


def test_declined_er_terminal_i_kontrakten():
    """Uden dette kan `commit_terminal_outcome(status="declined")` ikke kaldes."""
    import core.runtime.db_agent_contract as c

    assert "declined" in c.ASSIGNMENT_TERMINAL, (
        "declined mangler i ASSIGNMENT_TERMINAL — den terminale vej kan ikke "
        "baere barnets egen dom, og udfaldet maa lyve som 'completed'")


def test_opslag_paa_declined_giver_fase_og_kode():
    """En terminal status uden fase giver en tom etikette — samme hul som 18/11."""
    import core.runtime.db_agent_contract as c

    assert c._ERROR_PHASE.get("declined") == "capability"
    assert c._ERROR_CODE.get("declined") == "AGENT_DECLINED"
    assert c._SETTLING.get("declined") == "declined"


def test_commit_baerer_declined_og_skriver_det_i_outbox(isolated_runtime):
    """Assignmentet OG den ene terminalbesked skal begge sige `declined`."""
    c, conn = _contract_db()
    _indsæt_assignment(conn)

    out = c.commit_terminal_outcome(
        assignment_id="asg-decl", status="declined",
        summary="Jeg kunne ikke levere: værktøjet manglede.",
        error_code="AGENT_DECLINED", error_phase="capability")

    assert out.get("committed") is True, f"committet afvist: {out!r}"
    a = conn.execute("SELECT status FROM agent_assignments WHERE assignment_id='asg-decl'").fetchone()
    assert a["status"] == "declined", f"assignmentet stod {a['status']!r}"

    import json
    msg = conn.execute(
        "SELECT payload_json FROM agent_result_outbox WHERE assignment_id='asg-decl'").fetchone()
    assert msg is not None, "der blev ikke skrevet nogen terminalbesked"
    payload = json.loads(msg["payload_json"])
    assert payload["status"] == "declined", f"outbox sagde {payload['status']!r}"
    assert payload["error_code"] == "AGENT_DECLINED"


def test_settle_loefter_runnets_decline_op_i_assignmentet(isolated_runtime):
    """Den AEGTE vej: runnet erklaerer nul leverance, og udfaldet skal foelge med.

    Uden fixet blev assignmentet `completed`, fordi `target` kun kom fra
    `_SETTLING[registry_status]` — og registry-status er `completed` naar
    agenten har svaret.
    """
    import core.runtime.db_agent_contract as c

    conn = _contract_db()[1]
    _indsæt_assignment(conn)
    nu = "2026-11-23T10:00:00+00:00"

    # Agenten har svaret (registry = completed), men dens svar erklaerer at den
    # ikke leverede noget — den strukturelle form, ikke en tilfaeldig ordlyd.
    conn.execute(
        "INSERT INTO agent_registry (agent_id, status, role, goal, provider, model, "
        "persistent, last_error, created_at, updated_at) "
        "VALUES (?,?,?,?,?,?,?,?,?,?)",
        ("agent-decl", "completed", "executor", "goal", "claude-cli", "sonnet",
         0, "", nu, nu))
    conn.execute(
        "INSERT INTO agent_runs (run_id, agent_id, status, created_at, updated_at, "
        "assignment_id, error_code, error_phase) VALUES (?,?,?,?,?,?,?,?)",
        ("run-decl", "agent-decl", "completed", nu, nu, "asg-decl", "", ""))
    conn.execute(
        "INSERT INTO agent_messages (message_id, thread_id, run_id, agent_id, direction, "
        "role, content, kind, created_at) VALUES (?,?,?,?,?,?,?,?,?)",
        ("msg-decl", "th", "run-decl", "agent-decl", "agent->jarvis", "assistant",
         "Jeg har ikke målt noget: mine værktøjer er read-only.\n\nDÆKNING: ingen",
         "result", nu))
    conn.commit()

    c.settle_agent_status(agent_id="agent-decl", registry_status="completed")

    a = conn.execute("SELECT status FROM agent_assignments WHERE assignment_id='asg-decl'").fetchone()
    assert a["status"] == "declined", (
        f"assignmentet blev {a['status']!r} — barnets egen dom gik tabt "
        f"paa vejen til det lag foraelderen laeser")


def test_en_rigtig_leverance_bliver_stadig_completed(isolated_runtime):
    """Negativ kontrol: en agent der FAKTISK leverede maa ikke stemples declined."""
    import core.runtime.db_agent_contract as c

    conn = _contract_db()[1]
    _indsæt_assignment(conn, asg="asg-ok", agent="agent-ok")
    nu = "2026-11-23T10:00:00+00:00"

    conn.execute(
        "INSERT INTO agent_registry (agent_id, status, role, goal, provider, model, "
        "persistent, last_error, created_at, updated_at) "
        "VALUES (?,?,?,?,?,?,?,?,?,?)",
        ("agent-ok", "completed", "executor", "goal", "claude-cli", "sonnet",
         0, "", nu, nu))
    conn.execute(
        "INSERT INTO agent_runs (run_id, agent_id, status, created_at, updated_at, "
        "assignment_id, error_code, error_phase) VALUES (?,?,?,?,?,?,?,?)",
        ("run-ok", "agent-ok", "completed", nu, nu, "asg-ok", "", ""))
    conn.execute(
        "INSERT INTO agent_messages (message_id, thread_id, run_id, agent_id, direction, "
        "role, content, kind, created_at) VALUES (?,?,?,?,?,?,?,?,?)",
        ("msg-ok", "th", "run-ok", "agent-ok", "agent->jarvis", "assistant",
         "Jeg har rettet fejlen i koden og kørt testene: 14 grønne.\n\nDÆKNING: 2",
         "result", nu))
    conn.commit()

    c.settle_agent_status(agent_id="agent-ok", registry_status="completed")

    a = conn.execute("SELECT status FROM agent_assignments WHERE assignment_id='asg-ok'").fetchone()
    assert a["status"] == "completed", (
        f"en ægte leverance blev {a['status']!r} — vagten skal kun ramme "
        f"den agent der SELV melder nul leverance")
