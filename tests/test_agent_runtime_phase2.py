from __future__ import annotations

import importlib


def _load_agent_runtime():
    module = importlib.import_module("apps.api.jarvis_api.services.agent_runtime")
    return importlib.reload(module)


def test_agent_runtime_continues_dialog_and_records_result(isolated_runtime, monkeypatch) -> None:
    agent_runtime = _load_agent_runtime()

    monkeypatch.setattr(
        agent_runtime,
        "execute_cheap_lane",
        lambda message: {
            "text": "summary: follow-up handled\nfindings: task refined\nrecommendation: continue\nconfidence: high\nblockers: none",
            "status": "completed",
            "input_tokens": 12,
            "output_tokens": 18,
            "cost_usd": 0.0,
        },
    )

    agent = agent_runtime.spawn_agent_task(
        role="researcher",
        goal="Inspect the current runtime state",
        auto_execute=False,
    )
    updated = agent_runtime.send_message_to_agent(
        agent_id=str(agent["agent_id"]),
        content="Look specifically at the last council round and report back.",
    )

    assert updated["status"] == "completed"
    assert updated["message_count"] >= 3
    assert updated["latest_run"]["execution_mode"] == "solo-task"
    assert "follow-up handled" in updated["latest_message"]["content"]


def test_agent_runtime_schedules_and_runs_due_agents(isolated_runtime, monkeypatch) -> None:
    agent_runtime = _load_agent_runtime()

    monkeypatch.setattr(
        agent_runtime,
        "execute_cheap_lane",
        lambda message: {
            "text": "summary: watcher fired\nfindings: state changed\nrecommendation: notify Jarvis\nconfidence: medium\nblockers: none",
            "status": "completed",
            "input_tokens": 9,
            "output_tokens": 14,
            "cost_usd": 0.0,
        },
    )

    agent = agent_runtime.spawn_agent_task(
        role="watcher",
        goal="Watch the heartbeat cadence",
        persistent=True,
        auto_execute=False,
    )
    scheduled = agent_runtime.schedule_agent_task(
        agent_id=str(agent["agent_id"]),
        schedule_kind="once",
        delay_seconds=30,
    )
    fire_result = agent_runtime.run_due_agent_schedules(limit=10)

    assert scheduled["status"] == "scheduled"
    assert fire_result["triggered_count"] == 0

    isolated_runtime.db.update_agent_schedule(
        "agent-schedule-" + str(agent["agent_id"]),
        next_fire_at="2000-01-01T00:00:00+00:00",
    )
    due_result = agent_runtime.run_due_agent_schedules(limit=10)

    assert due_result["triggered_count"] == 1
    refreshed = agent_runtime.build_agent_detail_surface(str(agent["agent_id"]))
    assert refreshed is not None
    assert refreshed["message_count"] >= 4
    assert refreshed["latest_message"]["kind"] == "result"


def test_council_round_records_positions_and_synthesis(isolated_runtime, monkeypatch) -> None:
    agent_runtime = _load_agent_runtime()

    def fake_execute(message: str) -> dict[str, object]:
        if "critic" in message.lower():
            text = "summary: risk spotted\nrecommendation: revise\nconfidence: high\nvote: revise"
        else:
            text = "summary: workable path\nrecommendation: approve\nconfidence: medium\nvote: approve"
        return {
            "text": text,
            "status": "completed",
            "input_tokens": 11,
            "output_tokens": 16,
            "cost_usd": 0.0,
        }

    monkeypatch.setattr(agent_runtime, "execute_cheap_lane", fake_execute)

    council = agent_runtime.create_council_session_runtime(
        topic="Should Jarvis spawn a watcher for memory drift?",
        roles=["critic", "planner"],
    )
    updated = agent_runtime.run_council_round(str(council["council_id"]))

    assert updated["status"] == "reporting"
    assert updated["message_count"] >= 4
    assert "critic:" in updated["summary"]
    assert any(member["position_summary"] != "awaiting deliberation" for member in updated["members"])


def test_swarm_round_records_peer_handoffs_and_synthesis(isolated_runtime, monkeypatch) -> None:
    agent_runtime = _load_agent_runtime()

    def fake_execute(message: str) -> dict[str, object]:
        lowered = message.lower()
        if "swarm coordinator / synthesizer" in lowered:
            text = "summary: merged swarm view\nfindings: workers aligned\nrecommendation: proceed\nconfidence: high\nblockers: none"
        elif "critic" in lowered:
            text = 'summary: risk found\nrecommendation: hold\nconfidence: medium\nvote: hold'
        else:
            text = "summary: task shard completed\nrecommendation: proceed\nconfidence: medium\nvote: approve"
        return {
            "text": text,
            "status": "completed",
            "input_tokens": 10,
            "output_tokens": 15,
            "cost_usd": 0.0,
        }

    monkeypatch.setattr(agent_runtime, "execute_cheap_lane", fake_execute)

    swarm = agent_runtime.create_swarm_session_runtime(
        topic="Split repository inspection into parallel shards",
        roles=["planner", "critic", "synthesizer"],
    )
    updated = agent_runtime.run_swarm_round(str(swarm["council_id"]))

    assert updated["mode"] == "swarm"
    assert updated["status"] == "reporting"
    assert any(message["direction"] == "agent->agent" for message in updated["messages"])
    assert any(message["kind"] == "swarm-synthesis" for message in updated["messages"])
    assert "merged swarm view" in updated["summary"]
