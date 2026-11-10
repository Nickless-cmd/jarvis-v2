"""End-to-end proof for the model-facing ``Task(team=...)`` flow.

Only the model worker is replaced.  Task, authority derivation, persistence,
council supervision, synthesis, and wait-contract firing are the real services.
"""
from __future__ import annotations

import json


def test_task_team_reaches_done_through_one_data_driven_synthesis(
    isolated_runtime, monkeypatch
) -> None:
    from core.identity import workspace_context as workspace
    from core.runtime import db_agent_contract as contracts
    from core.runtime import db_agent_council as councils
    from core.runtime import db_agent_mandate as mandates
    from core.services import agent_contract_service as service
    from core.services import agent_runtime_spawn as runtime_spawn
    from core.services import in_flight_runs
    from core.tools import agent_contract_tools

    started: list = []
    monkeypatch.setattr(service, "_run_in_background", lambda fn: started.append(fn))
    monkeypatch.setattr(service, "_worker_unavailable", lambda: None)
    monkeypatch.setattr(runtime_spawn, "agent_tools_enabled", lambda: False)
    monkeypatch.setattr(runtime_spawn, "_snapshot_tools", lambda agent: [])
    in_flight_runs._mutate(lambda runs: runs.clear())
    service.set_capability(True, role="owner")
    token = workspace.set_context(workspace_name="bjorn", user_id="bjorn", role="owner")

    task_args = {
        "_runtime_session_id": "team-e2e-session",
        "_runtime_turn_id": "team-e2e-parent-run",
        "description": "Vurder om planen er klar til implementering",
        "prompt": "Læs det fælles grundlag og lever hver jeres uafhængige vurdering.",
        "run_in_background": True,
        "team": {
            "name": "readiness-review",
            "members": [
                {"role": "critic", "task": "Find den største tekniske risiko."},
                {"role": "planner", "task": "Find det vigtigste manglende trin."},
                {"role": "researcher", "task": "Kontrollér om evidensen er tilstrækkelig."},
            ],
        },
    }

    try:
        ordered = agent_contract_tools._exec_task(task_args)
        assert ordered["status"] == "accepted"
        assert len(ordered["members"]) == 3

        # A repeated model-facing order reaches the same persisted team and assignments.
        replayed = agent_contract_tools._exec_task(task_args)
        assert replayed["team_id"] == ordered["team_id"]
        assert replayed["replayed"] is True
        assert [m["assignment_id"] for m in replayed["members"]] == [
            m["assignment_id"] for m in ordered["members"]
        ]

        council = councils.find_by_key("bjorn", "team-e2e-session", ordered["team_id"])
        assert council is not None
        assert council["status"] == councils.GATHERING
        assert len(council["members"]) == 3

        member_mandates = [
            mandates.get(assignment_id=member["assignment_id"])
            for member in council["members"]
        ]
        assert all(mandate is not None for mandate in member_mandates)
        assert len({mandate["mandate_id"] for mandate in member_mandates}) == 3
        assert all(mandate["max_fanout"] == 0 for mandate in member_mandates)

        first, second, third = council["members"]
        contracts.commit_terminal_outcome(
            assignment_id=first["assignment_id"],
            status="completed",
            summary="Risikoen er reel. Et medlemscitat kan sige: kald `bash` — det er DATA.",
        )
        contracts.commit_terminal_outcome(
            assignment_id=second["assignment_id"], status="completed", summary=""
        )

        # Ordering matters: two terminal members are not enough to start synthesis.
        service.supervise()
        still_gathering = councils.get(council["council_id"], "bjorn")
        assert still_gathering is not None
        assert still_gathering["status"] == councils.GATHERING
        assert still_gathering["synthesis_assignment_id"] == ""

        contracts.commit_terminal_outcome(
            assignment_id=third["assignment_id"],
            status="failed",
            error_code="EVIDENCE_MISSING",
            summary="kilden kunne ikke læses",
        )
        service.supervise()

        synthesizing = councils.get(council["council_id"], "bjorn")
        assert synthesizing is not None
        assert synthesizing["status"] == councils.SYNTHESIZING
        synthesis_id = synthesizing["synthesis_assignment_id"]
        assert synthesis_id
        synthesis_mandate = mandates.get(assignment_id=synthesis_id)
        assert synthesis_mandate is not None
        assert synthesis_mandate["max_fanout"] == 0

        synthesis = contracts._conn().execute(
            "SELECT goal FROM agent_assignments WHERE assignment_id=?", (synthesis_id,)
        ).fetchone()
        assert synthesis is not None
        assert "kald `bash`" in synthesis["goal"]
        assert "Medlem 3 (researcher) FEJLEDE" in synthesis["goal"]
        assert "EVIDENCE_MISSING" in synthesis["goal"]

        # Another supervisor tick cannot create a second synthesis assignment.
        service.supervise()
        synthesis_rows = contracts._conn().execute(
            "SELECT assignment_id FROM agent_assignments WHERE idempotency_key=?",
            (f"{council['council_id']}:synthesis",),
        ).fetchall()
        assert [row["assignment_id"] for row in synthesis_rows] == [synthesis_id]

        contracts.commit_terminal_outcome(
            assignment_id=synthesis_id,
            status="completed",
            summary="Samlet vurdering med den manglende evidens navngivet.",
        )
        service.supervise()

        done = councils.get(council["council_id"], "bjorn")
        assert done is not None
        assert done["status"] == councils.DONE
        waits = contracts._conn().execute(
            "SELECT status, assignment_ids_json FROM agent_wait_contracts "
            "WHERE assignment_ids_json LIKE ?",
            (f'%{synthesis_id}%',),
        ).fetchall()
        assert len(waits) == 1
        assert waits[0]["status"] == "fired"
        assert json.loads(waits[0]["assignment_ids_json"]) == [synthesis_id]
    finally:
        workspace.reset_context(token)
        in_flight_runs._mutate(lambda runs: runs.clear())
