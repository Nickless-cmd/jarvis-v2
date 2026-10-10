from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor

from core.services import tool_execution_trace as trace


def _capture_timing(monkeypatch):
    sent: list[tuple[str, dict]] = []
    monkeypatch.setattr(
        "core.tools.tool_call_telemetry.udgiv_execution_timing",
        lambda payload: sent.append(("tool.execution_timing", payload)),
    )
    return sent


def test_surface_publishes_exactly_one_summary(monkeypatch):
    sent = _capture_timing(monkeypatch)

    trace.start_call("t1", tool="bash", run_id="r1", announced_at=10.0)
    trace.mark_dispatch("t1", now=10.025)
    trace.note_executor_timing(
        "t1",
        {
            "route": "server_persistent_shell",
            "dispatch_to_lock_ms": 40,
            "first_output_ms": 60,
            "process_ms": 90,
            "had_output": True,
        },
    )
    trace.mark_execution_complete("t1", now=10.140)
    trace.surface_result("t1", status="ok", exit_code=0, now=10.150)
    trace.surface_result("t1", status="ok", exit_code=0, now=10.200)

    assert [kind for kind, _ in sent] == ["tool.execution_timing"]
    assert sent[0][1] == {
        "tool": "bash",
        "run_id": "r1",
        "tool_use_id": "t1",
        "route": "server_persistent_shell",
        "status": "ok",
        "exit_code": 0,
        "had_output": True,
        "announced_to_dispatch_ms": 25,
        "dispatch_to_lock_ms": 40,
        "dispatch_to_spawn_ms": None,
        "first_output_ms": 60,
        "process_ms": 90,
        "process_exit_to_result_emit_ms": 10,
        "approval_wait_ms": None,
        "approved_dispatch_to_result_ms": None,
        "total_visible_ms": 150,
    }


def test_disabled_timing_and_unknown_ids_fail_soft(monkeypatch):
    sent = _capture_timing(monkeypatch)

    class Disabled:
        tool_execution_timing_enabled = False

    monkeypatch.setattr("core.runtime.settings.load_settings", lambda: Disabled())
    trace.start_call("disabled", tool="bash", run_id="r1", announced_at=1.0)
    trace.mark_dispatch("disabled", now=1.1)
    trace.surface_result("disabled", status="ok", now=1.2)
    trace.mark_dispatch("unknown", now=1.1)
    trace.mark_execution_complete("unknown", now=1.2)
    trace.note_executor_timing("unknown", {"process_ms": 5})
    trace.surface_result("unknown", status="error", now=1.3)
    assert sent == []


def test_output_flood_is_lossy_but_never_blocks():
    queue = trace.BoundedOutputBuffer(max_frames=2, max_pending_chars=12)
    for seq in range(1000):
        queue.put(trace.OutputDelta("t1", "stdout", seq, "abcdef"))

    drained = queue.drain()
    assert len(drained) <= 2
    assert sum(len(delta.chunk) for delta in drained) <= 12
    assert any(delta.truncated for delta in drained)


def test_two_producers_keep_buffer_bounded_and_timing_can_finish(monkeypatch):
    sent = _capture_timing(monkeypatch)
    queue = trace.BoundedOutputBuffer(max_frames=8, max_pending_chars=64)

    def produce(prefix: str) -> None:
        for seq in range(250):
            queue.put(trace.OutputDelta("threads", "stdout", seq, prefix * 4))

    trace.start_call("threads", tool="bash", run_id="r2", announced_at=20.0)
    with ThreadPoolExecutor(max_workers=2) as pool:
        list(pool.map(produce, ("a", "b")))
    trace.surface_result("threads", status="ok", exit_code=0, now=20.5)

    drained = queue.drain()
    assert len(drained) <= 8
    assert sum(len(delta.chunk) for delta in drained) <= 64
    assert sent[0][1]["total_visible_ms"] == 500


def test_bound_execution_routes_output_and_assigns_sequences():
    queue = trace.BoundedOutputBuffer()
    with trace.bind_execution("bound", queue):
        trace.emit_current_output("stdout", "a")
        trace.emit_current_output("stderr", "b")
    trace.emit_current_output("stdout", "outside")

    assert queue.drain() == [
        trace.OutputDelta("bound", "stdout", 1, "a"),
        trace.OutputDelta("bound", "stderr", 2, "b"),
    ]


def test_cancel_is_terminal_and_late_completion_cannot_publish(monkeypatch):
    sent = _capture_timing(monkeypatch)
    trace.start_call("cancelled", tool="bash", run_id="r3", announced_at=30.0)
    trace.cancel_call("cancelled", now=30.2)
    trace.mark_execution_complete("cancelled", now=30.3)
    trace.surface_result("cancelled", status="ok", exit_code=0, now=30.4)

    assert len(sent) == 1
    assert sent[0][1]["status"] == "cancelled"
    assert sent[0][1]["total_visible_ms"] == 200


def test_approval_wait_is_measured_separately_from_approved_execution(monkeypatch):
    sent = _capture_timing(monkeypatch)
    trace.start_call("approved", tool="bash", run_id="r4", announced_at=40.0)
    trace.mark_dispatch("approved", now=40.01)
    trace.mark_approval_wait("approved", now=40.02)
    trace.mark_approved_dispatch("approved", now=42.02)
    trace.mark_execution_complete("approved", now=42.12)
    trace.surface_result("approved", status="ok", now=42.13)

    assert sent[0][1]["approval_wait_ms"] == 2000
    assert sent[0][1]["approved_dispatch_to_result_ms"] == 110
