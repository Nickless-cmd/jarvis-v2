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


# --- Re-vurderingens dom (7/11-2026) ---------------------------------------
#
# Målt 7/11-2026: livsprojekter var den ENESTE initiativ-type der hverken
# udløber eller bliver grebet. `_expire_stale` springer dem bevidst over, og
# `tick_life_projects_reassessment` publicerede `life_projects.reassessment_due`
# — til en bus hvor nul abonnenter filtrerer paa det event. Saa et projekt
# kunne staa `pending` i syv maaneder uden ét forsøg, og ingen sagde det.
#
# Testene her maaler den ene ting der betyder noget: at re-vurderingen ender i
# en DOM. Ord doer, arbejde fornyes.

_DECAY_SETTINGS = {"layer_life_projects_enabled": True, "layer_life_projects_decay_days": 14}


def _monkeypatch_decay(monkeypatch) -> None:
    monkeypatch.setattr(
        "core.runtime.secrets.read_runtime_key",
        lambda key: _DECAY_SETTINGS.get(key),
    )


def test_revurdering_lukker_projekt_uden_spor(isolated_runtime, monkeypatch) -> None:
    from core.services import initiative_queue, life_projects

    _monkeypatch_decay(monkeypatch)
    iid = initiative_queue.seed_long_term_intention(title="Ord, ikke projekt", why="fordi")
    isolated_runtime.db.update_runtime_initiative(iid, updated_at="2026-05-15T11:11:18+00:00")

    udfald = life_projects.tick_life_projects_reassessment(trigger="test")

    record = isolated_runtime.db.get_runtime_initiative(iid)
    assert udfald["lukket"] == 1, "dommen fyrede ikke paa et projekt uden spor"
    assert record["status"] == "expired", "ord blev ikke lukket"
    assert "ord, ikke projekt" in str(record["blocked_reason"])


def test_revurdering_fornyer_projekt_med_spor(isolated_runtime, monkeypatch) -> None:
    from core.services import initiative_queue, life_projects

    _monkeypatch_decay(monkeypatch)
    iid = initiative_queue.seed_long_term_intention(title="Reelt arbejde", why="fordi")
    initiative_queue.mark_attempted(iid, blocked_reason="materialiseret i task")
    isolated_runtime.db.update_runtime_initiative(iid, updated_at="2026-05-15T11:11:18+00:00")

    udfald = life_projects.tick_life_projects_reassessment(trigger="test")

    record = isolated_runtime.db.get_runtime_initiative(iid)
    assert udfald["fornyet"] == 1, "et projekt med et forsoeg blev doemt som ord"
    assert record["status"] == "pending", "arbejde blev lukket i stedet for fornyet"


def test_revurdering_roerer_ikke_ferskt_projekt(isolated_runtime, monkeypatch) -> None:
    from core.services import initiative_queue, life_projects

    _monkeypatch_decay(monkeypatch)
    iid = initiative_queue.seed_long_term_intention(title="Helt ny", why="fordi")

    udfald = life_projects.tick_life_projects_reassessment(trigger="test")

    record = isolated_runtime.db.get_runtime_initiative(iid)
    assert udfald["reviewed"] == 0
    assert udfald["skipped"] == 1
    assert record["status"] == "pending"


def test_revurdering_lukker_projekt_med_gammelt_spor(isolated_runtime, monkeypatch) -> None:
    """Et spor fra i fjor holder ikke et projekt i live i dag.

    Maalt 7/11-2026: trust-projektet havde `last_action_at` fra en
    materialisering i oktober. Et «nogensinde»-kriterium ville goere det
    udoedeligt — dommen kunne aldrig lukke noget der bare var roert én gang.
    Spoergsmaalet er ikke om projektet nogensinde levede, men om det lever nu.
    """
    from core.services import initiative_queue, life_projects

    _monkeypatch_decay(monkeypatch)
    iid = initiative_queue.seed_long_term_intention(title="Gammelt spor", why="fordi")
    isolated_runtime.db.update_runtime_initiative(
        iid,
        last_attempt_at="2026-05-15T11:11:18+00:00",
        updated_at="2026-05-15T11:11:18+00:00",
    )

    udfald = life_projects.tick_life_projects_reassessment(trigger="test")

    record = isolated_runtime.db.get_runtime_initiative(iid)
    assert udfald["lukket"] == 1, "et forsoeg fra i fjor blev laest som livstegn i dag"
    assert record["status"] == "expired"


def test_visning_er_ikke_et_livstegn(isolated_runtime, monkeypatch) -> None:
    """At blive VIST er ikke at blive LOEFTET.

    Maalt 7/11-2026: `proactivity_bridge.py:321` kalder
    `mark_acted(..., action_summary="surfaced via proactivity_bridge")`, og
    `runtime_action_executor.py:526` kalder den med "promoted-to-visible-lane".
    Begge skriver `last_action_at`. Da dommen laeste det felt som et spoer, fik
    et projekt 14 nye dage for at blive vist — praecis den fejlklasse
    `mark_acted`-fixet 1/11 skulle afskaffe.

    Testen kalder den RIGTIGE `mark_acted` (ikke en haandskrevet raekke), saa
    den maaler koblingen til den funktion der faktisk skriver feltet.
    """
    from core.services import initiative_queue, life_projects

    _monkeypatch_decay(monkeypatch)
    iid = initiative_queue.seed_long_term_intention(title="Kun vist", why="fordi")
    initiative_queue.mark_acted(iid, action_summary="surfaced via proactivity_bridge")
    isolated_runtime.db.update_runtime_initiative(iid, updated_at="2026-05-15T11:11:18+00:00")

    udfald = life_projects.tick_life_projects_reassessment(trigger="test")

    record = isolated_runtime.db.get_runtime_initiative(iid)
    assert udfald["lukket"] == 1, "en visning blev laest som et livstegn"
    assert record["status"] == "expired", "projektet overlevede paa at blive vist"
