"""G: legacy_unscoped-agenter koerer uaendret efter migrationen og alle G1-G5-aendringer.

Skemaet bygges FOER kontrakt-kolonnerne findes (som CT105's: 363 agenter / 1.540 runs, alle legacy_unscoped, ingen
persistente), raekkerne sættes ind, og FOERST DEREFTER koerer den additive migration og hver ny kodesti."""
from __future__ import annotations

import pytest

TABLES_THAT_MUST_STAY_EMPTY = ("agent_assignments", "agent_result_outbox", "agent_route_decisions",
                               "agent_fork_contexts", "agent_leases", "agent_wait_contracts")


@pytest.fixture
def legacy(isolated_runtime, monkeypatch):
    import core.runtime.db_agent_contract as c
    import core.runtime.db_agent_runtime as rt
    from core.runtime.db_core import connect
    import core.services.agent_runtime as ar

    conn = connect()
    rt._ensure_agent_runtime_tables(conn)                      # det gamle skema, uden kontrakt-kolonner
    assert "owner_user_id" not in {r[1] for r in conn.execute("PRAGMA table_info(agent_registry)")}
    conn.commit()
    for i in range(6):
        rt.create_agent_registry_entry(
            agent_id=f"leg-{i}", role="researcher", goal=f"g{i}", provider="copilot-premium", model="m1",
            status="completed", persistent=(i >= 4), ttl_seconds=900 if i >= 4 else 0,
            next_wake_at="2026-10-07T00:00:00+00:00" if i >= 4 else "")
        rt.create_agent_run(run_id=f"run-leg-{i}", agent_id=f"leg-{i}", status="completed")
    rt.create_agent_schedule(schedule_id="agent-schedule-leg-4", agent_id="leg-4", schedule_kind="interval-seconds",
                             schedule_expr="900", next_fire_at="2026-10-07T00:00:00+00:00", active=True)
    c._ENSURED.clear()
    calls = []
    monkeypatch.setattr(ar, "execute_with_role_or_fallback",
                        lambda **kw: calls.append(kw) or {"text": "vagten svarer", "status": "completed"})

    class H:
        c_, rt_, calls_ = c, rt, calls

        def n(self, table, where="1=1"):
            return c._conn().execute(f"SELECT COUNT(*) FROM {table} WHERE {where}").fetchone()[0]
    return H()


def test_the_migration_keeps_every_legacy_row_marked_legacy_unscoped(legacy):
    legacy.c_._conn()
    assert legacy.n("agent_registry") == 6 and legacy.n("agent_runs") == 6
    assert legacy.n("agent_registry", "owner_user_id='legacy_unscoped'") == 6
    assert legacy.n("agent_runs", "owner_user_id='legacy_unscoped' AND assignment_id=''") == 6
    assert {k: legacy.n(k) for k in TABLES_THAT_MUST_STAY_EMPTY} == {k: 0 for k in TABLES_THAT_MUST_STAY_EMPTY}
    assert {"message_kind", "state_code", "resolved_at"} <= {
        r[1] for r in legacy.c_._conn().execute("PRAGMA table_info(agent_result_outbox)")}


def test_every_new_code_path_leaves_legacy_agents_alone(legacy):
    from core.runtime.db_agent_attempts import live_run_id
    from core.runtime.db_agent_lease import reconcile_expired_leases
    from core.runtime.db_agent_outcome_unknown import is_blocked
    from core.services.agent_activation import ensure_activation
    from core.services.agent_model_router import bound_owner
    from core.services.prompt_sections.agent_orchestration import orchestrator_state

    legacy.c_._conn()
    for i in range(6):
        aid = f"leg-{i}"
        assert bound_owner(aid) == "" and live_run_id(f"run-leg-{i}") == f"run-leg-{i}"
        assert ensure_activation(aid) == {"status": "not_applicable"} and is_blocked(aid) is False
        for status in ("completed", "failed", "cancelled", "expired", "scheduled"):
            assert legacy.c_.settle_agent_status(agent_id=aid, registry_status=status) is None
    assert reconcile_expired_leases() == []
    assert orchestrator_state(owner_user_id="bjorn", session_id="s1") == ""
    assert {k: legacy.n(k) for k in TABLES_THAT_MUST_STAY_EMPTY} == {k: 0 for k in TABLES_THAT_MUST_STAY_EMPTY}


def test_a_legacy_model_call_has_no_owner_argument_and_creates_no_failover_run(legacy):
    from core.services import agent_model_router as M

    class Boom:
        def execute_with_role_or_fallback(self, **kw):
            raise M.ModelCallFailed("nede", provider=kw["provider"], model=kw["model"])
    legacy.c_._conn()
    with pytest.raises(M.ModelCallFailed):
        M.call_agent_model(agent={"agent_id": "leg-0", "provider": "copilot-premium", "model": "m1",
                                  "tool_policy": ""}, facade=Boom(), run_id="run-leg-0", provider="copilot-premium",
                           model="m1", requires_tools=False, messages=[], lane="agent")
    assert legacy.n("agent_runs") == 6 and legacy.n("agent_route_decisions") == 0


def test_a_persistent_legacy_watcher_still_runs_on_its_schedule_without_any_contract_rows(legacy):
    import core.services.agent_runtime_spawn as sp
    legacy.c_._conn()
    out = sp.run_due_agent_schedules(limit=5)
    assert out["triggered_count"] == 1 and len(legacy.calls_) == 1
    assert "owner_user_id" not in legacy.calls_[0]                    # den gamle sti, ingen ejer-guard
    assert {k: legacy.n(k) for k in TABLES_THAT_MUST_STAY_EMPTY} == {k: 0 for k in TABLES_THAT_MUST_STAY_EMPTY}
    assert legacy.n("agent_runs", "agent_id='leg-4'") == 2            # det gamle run + det nye, intet failover-run
    assert legacy.rt_.get_agent_registry_entry("leg-4")["owner_user_id"] == "legacy_unscoped"
