"""Laeringsplanen skal kunne blive til opgaver.

15/9-2026: `create_task(run_id=)` blev omdoebt til `origin_ref` i 4b53916a3.
`materialize_learning_curriculum_tasks` sendte stadig `run_id`, fik TypeError
hver gang, og hjerteslagets `except: pass` slugte den. To doegn uden en
eneste curriculum-opgave. Testen kalder den RIGTIGE create_task.
"""
from __future__ import annotations

import json


def test_laeringsplanen_bliver_til_en_opgave_med_ophav(isolated_runtime):
    isolated_runtime.db.upsert_cognitive_personality_vector(
        confidence_by_domain=json.dumps({"repo_reasoning": 0.2, "planning": 0.35}),
        recurring_mistakes=json.dumps(["Svar bliver for lange i simple repo-opgaver"]),
    )
    from core.services.self_experiments import materialize_learning_curriculum_tasks

    ud = materialize_learning_curriculum_tasks(
        limit=3, origin="heartbeat:curriculum", owner="heartbeat-runtime",
        run_id="heartbeat-tick:abc",
    )

    assert int(ud["created"]) >= 1
    opgave = isolated_runtime.db.get_runtime_task(str(ud["task_ids"][0]))
    assert opgave["kind"] == "curriculum-focus"
    # Tick-id'et er OPHAV, ikke en koersel — derfor origin_ref.
    assert opgave.get("origin_ref") == "heartbeat-tick:abc"
