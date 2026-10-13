from __future__ import annotations


def test_runtime_awareness_tracks_new_runtime_organs(isolated_runtime) -> None:
    event_bus = __import__("core.eventbus.bus", fromlist=["event_bus"]).event_bus
    runtime_tasks = __import__(
        "core.services.runtime_tasks",
        fromlist=["create_task"],
    )
    runtime_flows = __import__(
        "core.services.runtime_flows",
        fromlist=["create_flow"],
    )
    runtime_browser_body = __import__(
        "core.services.runtime_browser_body",
        fromlist=["ensure_browser_body"],
    )
    awareness = __import__(
        "core.services.runtime_awareness_signal_tracking",
        fromlist=["track_runtime_awareness_signals_for_visible_turn"],
    )
    bootstrap = __import__(
        "core.identity.workspace_bootstrap",
        fromlist=["workspace_memory_paths"],
    )

    task = runtime_tasks.create_task(
        kind="analysis",
        goal="Inspect integration gaps",
        origin="test",
        owner="test",
    )
    runtime_flows.create_flow(
        task_id=task["task_id"],
        current_step="inspect-gaps",
        step_state="queued",
        plan=[{"step": "inspect-gaps", "status": "queued"}],
        next_action="Continue bounded inspection.",
    )
    runtime_browser_body.ensure_browser_body(
        profile_name="jarvis-browser",
        active_task_id=task["task_id"],
    )
    event_bus.publish(
        "heartbeat.initiative_pushed",
        {"focus": "Follow a live initiative", "priority": "high"},
    )
    paths = bootstrap.workspace_memory_paths()
    paths["daily_memory"].write_text("Daily memory is present.\n", encoding="utf-8")

    tracked = awareness.track_runtime_awareness_signals_for_visible_turn(
        session_id="session-test",
        run_id="run-test",
    )

    canonical = {
        item["canonical_key"]: item
        for item in tracked["items"]
    }

    assert "runtime-awareness:runtime-task-backlog" in canonical
    assert canonical["runtime-awareness:runtime-task-backlog"]["status"] == "active"
    assert "runtime-awareness:runtime-flow-orchestration" in canonical
    assert canonical["runtime-awareness:runtime-flow-orchestration"]["status"] == "active"
    assert "runtime-awareness:runtime-hook-bridge" in canonical
    assert canonical["runtime-awareness:runtime-hook-bridge"]["status"] == "constrained"
    assert "runtime-awareness:browser-body" in canonical
    assert canonical["runtime-awareness:browser-body"]["status"] == "active"
    assert "runtime-awareness:layered-memory" in canonical
    assert canonical["runtime-awareness:layered-memory"]["status"] == "active"


def test_runtime_awareness_marks_blocked_runtime_work_constrained(isolated_runtime) -> None:
    runtime_tasks = __import__(
        "core.services.runtime_tasks",
        fromlist=["create_task", "update_task"],
    )
    awareness = __import__(
        "core.services.runtime_awareness_signal_tracking",
        fromlist=["track_runtime_awareness_signals_for_visible_turn"],
    )

    task = runtime_tasks.create_task(
        kind="analysis",
        goal="Recover blocked work",
        origin="test",
        owner="test",
    )
    runtime_tasks.update_task(
        task["task_id"],
        status="blocked",
        blocked_reason="Need orchestration attention",
    )

    tracked = awareness.track_runtime_awareness_signals_for_visible_turn(
        session_id="session-test",
        run_id="run-test-2",
    )

    canonical = {
        item["canonical_key"]: item
        for item in tracked["items"]
    }
    assert canonical["runtime-awareness:runtime-task-backlog"]["status"] == "constrained"


def test_surface_cache_overlever_et_helt_warmer_tick(isolated_runtime, monkeypatch) -> None:
    """Surface-cachen skal være varm når prompt_assembly_cache_warmer fyrer igen.

    Målt 13/10-2026: TTL'en stod på 120 s, mens warmerens ticks lå 259-297 s
    fra hinanden (journal 14:00-14:19). Cachen udløb derfor i hullet mellem to
    ticks, og både warmeren og enhver visible tur i hullet betalte den fulde
    kolde genopbygning (~1,15 GB læst pr. gang, målt med strace).
    """
    tracking = __import__(
        "core.services.runtime_awareness_signal_tracking",
        fromlist=["build_runtime_awareness_signal_surface"],
    )

    class _Uur:
        t = 0.0

        def monotonic(self) -> float:
            return self.t

    ur = _Uur()
    monkeypatch.setattr(tracking, "_time", ur)
    monkeypatch.setattr(tracking, "_surface_cache_by_limit", {})

    foerste = tracking.build_runtime_awareness_signal_surface(limit=8)
    ur.t = 297.0  # længste målte interval mellem to warmer-ticks
    andet = tracking.build_runtime_awareness_signal_surface(limit=8)

    assert andet is foerste, (
        "surface-cachen udløb før warmerens næste tick — TTL-kollisionen er tilbage"
    )
