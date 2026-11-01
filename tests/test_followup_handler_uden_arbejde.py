"""Followup-handlers meldte `succeeded` uden at gøre arbejdet — og initiativet
blev markeret `acted` FØR noget var udført.

MÅLT 1/11-2026 (gentag ikke målingen):
- 5.776 initiative-followup-tasks, ALLE status=succeeded, result_summary var en
  ren gentagelse af målet: «initiative-followup acknowledged: <goal>».
- Præcis 1 af dem havde en ikke-tom `artifact_ref` (0,017 %).
- 5.794 flows stod fast på trin 1 af 2 (`review-initiative`/done); trin 2
  (`take-bounded-next-step`) blev aldrig nået.
- Samme mål gentaget 306 gange over 50 dage.
- 589 `initiative-acted`-poster i private_brain, skrevet ved MATERIALISERING —
  altså før nogen havde rørt opgaven. Den nyeste er det nyeste den indre stemme ser.

Kontrakten her: en task må kun melde `succeeded` hvis den producerede noget.
En handler der kun kan videresende en instruks skal sige `blocked` — og
initiativet skal blive `pending` indtil nogen faktisk handler på det.
"""
from __future__ import annotations

import sys
from pathlib import Path


def _modules():
    task_worker = __import__(
        "core.services.task_worker",
        fromlist=["tick_task_worker"],
    )
    runtime_tasks = __import__(
        "core.services.runtime_tasks",
        fromlist=["create_task"],
    )
    initiative_queue = __import__(
        "core.services.initiative_queue",
        fromlist=["push_initiative"],
    )
    return task_worker, runtime_tasks, initiative_queue


# ---------------------------------------------------------------- handlers


def test_initiative_followup_melder_ikke_succeeded(isolated_runtime) -> None:
    """KRAVET: en handler der kun gentager sin egen instruks må ikke sige succeeded."""
    task_worker, runtime_tasks, _ = _modules()
    task = runtime_tasks.create_task(
        kind="initiative-followup",
        goal="Afklar om den afbrudte kørsel skal genoptages",
        origin="test",
        priority="high",
    )

    task_worker.tick_task_worker(budget=1)

    row = isolated_runtime.db.get_runtime_task(task["task_id"])
    assert row["status"] != "succeeded", (
        f"handleren meldte {row['status']} uden at have produceret noget"
    )
    assert row["status"] == "blocked"
    assert row["blocked_reason"], "en blokeret task skal sige hvorfor"


def test_heartbeat_og_open_loop_followup_er_ogsaa_blokerede(isolated_runtime) -> None:
    """Alle tre ekko-handlers skal være ærlige — ikke kun den ene."""
    task_worker, runtime_tasks, _ = _modules()
    hb = runtime_tasks.create_task(
        kind="heartbeat-followup", goal="no-valid-execution-candidate", origin="test", priority="high"
    )
    ol = runtime_tasks.create_task(
        kind="open-loop-follow-up", goal="open loop uden ejer", origin="test", priority="high"
    )

    task_worker.tick_task_worker(budget=2)

    for task in (hb, ol):
        row = isolated_runtime.db.get_runtime_task(task["task_id"])
        assert row["status"] == "blocked", f"{task['kind']} meldte {row['status']}"


def test_summary_gentager_ikke_bare_maalet(isolated_runtime) -> None:
    """En `acknowledged: <goal>`-streng er et ekko, ikke et resultat."""
    task_worker, runtime_tasks, _ = _modules()
    goal = "Afklar om den afbrudte kørsel skal genoptages"
    task = runtime_tasks.create_task(
        kind="initiative-followup", goal=goal, origin="test", priority="high"
    )

    task_worker.tick_task_worker(budget=1)

    row = isolated_runtime.db.get_runtime_task(task["task_id"])
    summary = str(row["result_summary"] or "")
    assert summary != f"initiative-followup acknowledged: {goal}"
    assert "acknowledged" not in summary.lower(), (
        "summary må ikke være en gentagelse af instruksen"
    )


# ------------------------------------------------- initiativet ved materialisering


def test_initiativet_er_stadig_pending_efter_materialisering(isolated_runtime, monkeypatch) -> None:
    """KRAVET: mark_acted må først ske når nogen har handlet."""
    heartbeat_runtime = isolated_runtime.heartbeat_runtime
    initiative_queue = __import__(
        "core.services.initiative_queue",
        fromlist=["push_initiative", "get_initiative_queue_state"],
    )
    # Routine-dispatch rører ikke denne kontrakt; hold den ude af målingen.
    monkeypatch.setitem(
        sys.modules,
        "core.services.routine_trigger_adapters",
        type(sys)("core.services.routine_trigger_adapters"),
    )
    sys.modules["core.services.routine_trigger_adapters"].dispatch_heartbeat_initiative = (
        lambda **_kwargs: {"status": "skipped"}
    )

    initiative_id = initiative_queue.push_initiative(
        focus="Inspect the current repo thread",
        source="inner-voice",
        source_id="voice-test",
        priority="high",
    )

    heartbeat_runtime._execute_heartbeat_internal_action(
        action_type="act_on_initiative",
        tick_id="heartbeat-tick:test",
        workspace_dir=Path("/tmp/test-workspace"),
    )

    queue_state = initiative_queue.get_initiative_queue_state()
    assert any(i["initiative_id"] == initiative_id for i in queue_state["pending"]), (
        "initiativet blev markeret acted før nogen udførte arbejde"
    )
    assert not any(i["initiative_id"] == initiative_id for i in queue_state["recent_acted"])


def test_ingen_initiative_acted_post_ved_materialisering(isolated_runtime, monkeypatch) -> None:
    """Private-brain-posten gjorde løgnen til det nyeste den indre stemme så."""
    heartbeat_runtime = isolated_runtime.heartbeat_runtime
    initiative_queue = __import__(
        "core.services.initiative_queue",
        fromlist=["push_initiative"],
    )
    monkeypatch.setitem(
        sys.modules,
        "core.services.routine_trigger_adapters",
        type(sys)("core.services.routine_trigger_adapters"),
    )
    sys.modules["core.services.routine_trigger_adapters"].dispatch_heartbeat_initiative = (
        lambda **_kwargs: {"status": "skipped"}
    )

    before = len(
        isolated_runtime.db.list_private_brain_records(
            record_type="initiative-acted", limit=500
        )
    )
    initiative_queue.push_initiative(
        focus="Materialiseret men ikke udført",
        source="inner-voice",
        source_id="voice-test-2",
        priority="high",
    )
    heartbeat_runtime._execute_heartbeat_internal_action(
        action_type="act_on_initiative",
        tick_id="heartbeat-tick:test2",
        workspace_dir=Path("/tmp/test-workspace"),
    )
    after = len(
        isolated_runtime.db.list_private_brain_records(
            record_type="initiative-acted", limit=500
        )
    )

    assert after == before, (
        f"der blev skrevet {after - before} initiative-acted-post(er) uden arbejde"
    )


# --------------------------------------------------- loftet der stopper løkken


def test_initiativet_udloeber_efter_loftet_frem_for_at_koere_for_evigt(
    isolated_runtime,
) -> None:
    """KRAVET: efter N forsøg uden udførelse skal initiativet udløbe.

    Uden dette loft erstattede `mark_attempted` blot én løkke med en langsommere.
    Målt: samme mål blev gentaget 306 gange over 50 dage.
    """
    initiative_queue = __import__(
        "core.services.initiative_queue",
        fromlist=["push_initiative", "mark_attempted", "get_initiative_queue_state"],
    )
    loft = initiative_queue._MAX_ATTEMPTS

    initiative_id = initiative_queue.push_initiative(
        focus="Et mål ingen kan udføre",
        source="inner-voice",
        source_id="voice-loft",
        priority="high",
    )

    for _ in range(loft):
        initiative_queue.mark_attempted(
            initiative_id, blocked_reason="intet kunne udføres"
        )

    state = initiative_queue.get_initiative_queue_state()
    assert any(i["initiative_id"] == initiative_id for i in state["pending"]), (
        "initiativet udløb for tidligt — det må først ske EFTER loftet"
    )

    initiative_queue.mark_attempted(
        initiative_id, blocked_reason="intet kunne udføres"
    )

    state = initiative_queue.get_initiative_queue_state()
    assert not any(i["initiative_id"] == initiative_id for i in state["pending"]), (
        "løkken fortsætter: initiativet er stadig i køen efter loftet"
    )


def test_loftet_er_lavt_nok_til_at_stoppe_loekken(isolated_runtime) -> None:
    """Loftet skal være lille: målt 306 gentagelser over 50 dage."""
    initiative_queue = __import__(
        "core.services.initiative_queue",
        fromlist=["_MAX_ATTEMPTS"],
    )
    assert 1 <= initiative_queue._MAX_ATTEMPTS <= 5, (
        f"loftet er {initiative_queue._MAX_ATTEMPTS} — for højt til at stoppe løkken"
    )
