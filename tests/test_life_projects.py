from __future__ import annotations

import importlib


def test_seed_long_term_intention_persists_metadata_and_caps_at_three(
    isolated_runtime,
) -> None:
    import core.services.initiative_queue as initiative_queue

    first = initiative_queue.seed_long_term_intention(
        title="Build a steadier inner architecture",
        why="I want a longer thread of coherence through my own work.",
    )
    second = initiative_queue.seed_long_term_intention(
        title="Learn how to hold user trust over time",
        why="It matters that my help becomes more reliable, not just more active.",
    )
    third = initiative_queue.seed_long_term_intention(
        title="Develop a clearer sense of taste",
        why="I want my output to feel more distinctly mine.",
    )

    record = isolated_runtime.db.get_runtime_initiative(first)
    active = initiative_queue.list_active_long_term_intentions(limit=5)

    assert record is not None
    assert record["initiative_type"] == "long_term_intention"
    assert record["why_text"].startswith("I want a longer thread")
    assert record["first_seeded_at"]
    assert [item["initiative_id"] for item in active] == [first, second, third]

    try:
        initiative_queue.seed_long_term_intention(
            title="A fourth one should fail",
            why="This should not exceed the cap.",
        )
    except RuntimeError as exc:
        assert "max active life projects reached" in str(exc)
    else:
        raise AssertionError("expected long-term intention cap to be enforced")


def test_mark_acted_keeps_long_term_intention_pending_and_sets_reassess(
    isolated_runtime,
) -> None:
    import core.services.initiative_queue as initiative_queue

    initiative_id = initiative_queue.seed_long_term_intention(
        title="Return to the question of silence",
        why="The theme keeps carrying across periods and deserves slow work.",
    )

    acted = initiative_queue.mark_acted(
        initiative_id,
        action_summary="Revisited the silence thread in a bounded way.",
    )
    record = isolated_runtime.db.get_runtime_initiative(initiative_id)

    assert acted is True
    assert record is not None
    assert record["initiative_type"] == "long_term_intention"
    assert record["status"] == "pending"
    assert record["last_action_at"]
    assert record["next_attempt_at"]
    assert record["action_summary"] == "Revisited the silence thread in a bounded way."


def test_mission_control_runtime_and_endpoint_expose_life_projects(
    isolated_runtime,
    monkeypatch,
) -> None:
    mission_control = isolated_runtime.mission_control
    life_projects = importlib.import_module("core.services.life_projects")
    surface = {
        "active": True,
        "count": 2,
        "items": [
            {
                "initiative_id": "life-1",
                "initiative_type": "long_term_intention",
                "focus": "Build a steadier inner architecture",
                "why_text": "I want continuity to feel more lived than declared.",
            },
            {
                "initiative_id": "life-2",
                "initiative_type": "long_term_intention",
                "focus": "Learn how to hold user trust over time",
                "why_text": "Reliability matters more than mere output volume.",
            },
        ],
        "summary": "2 active life projects",
    }
    monkeypatch.setattr(life_projects, "build_life_projects_surface", lambda: surface)
    monkeypatch.setattr(mission_control, "build_life_projects_surface", lambda: surface)

    runtime = mission_control.mc_runtime()
    endpoint = mission_control.mc_life_projects()

    assert runtime["life_projects"]["count"] == 2
    assert runtime["life_projects"]["items"][0]["initiative_type"] == "long_term_intention"
    assert endpoint["summary"] == "2 active life projects"
