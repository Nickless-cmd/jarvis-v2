from __future__ import annotations

from core.services.tool_chip_payload import build_tool_capability_payload
from core.services.tool_failure_surface import normalise_tool_failure


def test_timeout_has_a_visible_cause():
    assert normalise_tool_failure(
        "error", "", {"status": "error", "error": "timeout"}, timeout_s=120
    ) == "Timeout efter 120 sekunder"


def test_nonzero_exit_keeps_stderr():
    text = normalise_tool_failure(
        "error", "", {"exit_code": 2, "stderr": "fil mangler"}
    )
    assert "exit code 2" in text
    assert "fil mangler" in text


def test_tool_payload_replaces_empty_error_with_concrete_cause():
    payload = build_tool_capability_payload(
        tool="bash",
        status="error",
        result_text="",
        raw_result={"exit_code": 2, "stderr": "fil mangler"},
    )
    assert "exit code 2" in payload["result_text"]
    assert "fil mangler" in payload["result_text"]


def test_tool_lifecycle_finishes_once_with_concrete_error(monkeypatch):
    from core.services import live_job_events
    from core.services import tool_execution_trace as trace

    live_job_events.reset_for_tests()
    monkeypatch.setattr(
        "core.tools.tool_call_telemetry.udgiv_execution_timing", lambda _payload: None
    )
    subscription = live_job_events.subscribe(session_id="session-9", after=0)
    trace.start_call(
        "call-9", tool="operator_bash", run_id="run-9", session_id="session-9"
    )
    trace.surface_result(
        "call-9",
        status="error",
        exit_code=2,
        result_text="",
        raw_result={"exit_code": 2, "stderr": "fil mangler"},
    )
    trace.surface_result("call-9", status="ok")

    events = [subscription.queue.get_nowait(), subscription.queue.get_nowait()]
    assert [event.event_type for event in events] == ["job_started", "job_finished"]
    assert all(event.source == "tool_operator" for event in events)
    assert events[1].payload["status"] == "error"
    assert "exit code 2" in events[1].payload["result_text"]
    assert "fil mangler" in events[1].payload["result_text"]
    assert subscription.queue.empty()
    subscription.close()
