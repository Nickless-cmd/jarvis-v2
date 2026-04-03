from __future__ import annotations

import importlib
import json


def _parse_sse(chunks: list[str], event_name: str) -> list[dict[str, object]]:
    parsed: list[dict[str, object]] = []
    for chunk in chunks:
        lines = [line.strip() for line in chunk.strip().splitlines() if line.strip()]
        if len(lines) < 2:
            continue
        if lines[0] != f"event: {event_name}":
            continue
        if not lines[1].startswith("data: "):
            continue
        parsed.append(json.loads(lines[1][6:]))
    return parsed


def _run_visible_stream(
    *,
    visible_runs,
    visible_model,
    monkeypatch,
    text: str,
    run_id: str,
) -> tuple[list[str], dict[str, object]]:
    monkeypatch.setattr(visible_runs, "record_cost", lambda **kwargs: None)
    monkeypatch.setattr(
        visible_runs, "_track_runtime_candidates", lambda run, assistant_text: None
    )
    monkeypatch.setattr(
        visible_runs, "_persist_session_assistant_message", lambda run, message: None
    )

    def stub_stream_visible_model(**kwargs):
        yield visible_model.VisibleModelDelta(delta=text)
        yield visible_model.VisibleModelStreamDone(
            result=visible_model.VisibleModelResult(
                text=text,
                input_tokens=1,
                output_tokens=1,
                cost_usd=0.0,
            )
        )

    monkeypatch.setattr(visible_runs, "stream_visible_model", stub_stream_visible_model)

    run = visible_runs.VisibleRun(
        run_id=run_id,
        lane="local",
        provider="phase1-runtime",
        model="stub",
        user_message="smoke",
        session_id="session-smoke",
    )

    async def collect() -> list[str]:
        chunks: list[str] = []
        async for chunk in visible_runs._stream_visible_run(run):
            chunks.append(chunk)
        return chunks

    import asyncio

    chunks = asyncio.run(collect())
    return chunks, visible_runs.get_last_visible_capability_use() or {}


def test_visible_run_executes_read_capability_and_surfaces_result(
    isolated_runtime,
    monkeypatch,
) -> None:
    visible_runs = importlib.import_module("apps.api.jarvis_api.services.visible_runs")
    visible_runs = importlib.reload(visible_runs)
    visible_model = importlib.import_module("apps.api.jarvis_api.services.visible_model")
    chunks, last_use = _run_visible_stream(
        visible_runs=visible_runs,
        visible_model=visible_model,
        monkeypatch=monkeypatch,
        text='<capability-call id="tool:read-workspace-user-profile" />',
        run_id="visible-cap-read",
    )

    capability_events = _parse_sse(chunks, "capability")
    delta_events = _parse_sse(chunks, "delta")

    assert capability_events
    assert capability_events[-1]["capability_id"] == "tool:read-workspace-user-profile"
    assert capability_events[-1]["status"] == "executed"
    assert capability_events[-1]["execution_mode"] == "workspace-file-read"
    assert any("# USER" in str(item.get("delta") or "") for item in delta_events)
    assert last_use.get("capability_id") == "tool:read-workspace-user-profile"
    assert last_use.get("status") == "executed"


def test_visible_run_surfaces_gated_write_capability_without_execution(
    isolated_runtime,
    monkeypatch,
) -> None:
    visible_runs = importlib.import_module("apps.api.jarvis_api.services.visible_runs")
    visible_runs = importlib.reload(visible_runs)
    visible_model = importlib.import_module("apps.api.jarvis_api.services.visible_model")
    chunks, last_use = _run_visible_stream(
        visible_runs=visible_runs,
        visible_model=visible_model,
        monkeypatch=monkeypatch,
        text='<capability-call id="tool:propose-workspace-memory-update" />',
        run_id="visible-cap-write",
    )

    capability_events = _parse_sse(chunks, "capability")
    delta_events = _parse_sse(chunks, "delta")

    assert capability_events
    assert capability_events[-1]["capability_id"] == "tool:propose-workspace-memory-update"
    assert capability_events[-1]["status"] == "approval-required"
    assert capability_events[-1]["execution_mode"] == "workspace-file-write"
    assert any(
        "Capability requires explicit approval" in str(item.get("delta") or "")
        for item in delta_events
    )
    assert all(
        '<capability-call id="tool:propose-workspace-memory-update" />'
        not in str(item.get("delta") or "")
        for item in delta_events
    )
    assert last_use.get("capability_id") == "tool:propose-workspace-memory-update"
    assert last_use.get("status") == "approval-required"


def test_visible_run_consumes_prose_plus_capability_without_raw_tag_leakage(
    isolated_runtime,
    monkeypatch,
) -> None:
    visible_runs = importlib.import_module("apps.api.jarvis_api.services.visible_runs")
    visible_runs = importlib.reload(visible_runs)
    visible_model = importlib.import_module("apps.api.jarvis_api.services.visible_model")

    chunks, last_use = _run_visible_stream(
        visible_runs=visible_runs,
        visible_model=visible_model,
        monkeypatch=monkeypatch,
        text=(
            'Jeg læser nu profilen. '
            '<capability-call id="tool:read-workspace-user-profile" /> '
            'Jeg vender tilbage.'
        ),
        run_id="visible-cap-prose-mixed",
    )

    capability_events = _parse_sse(chunks, "capability")
    delta_events = _parse_sse(chunks, "delta")

    assert capability_events
    assert capability_events[-1]["capability_id"] == "tool:read-workspace-user-profile"
    assert any("# USER" in str(item.get("delta") or "") for item in delta_events)
    assert all("<capability-call" not in str(item.get("delta") or "") for item in delta_events)
    assert last_use.get("capability_id") == "tool:read-workspace-user-profile"


def test_visible_run_selects_first_known_capability_when_multiple_are_emitted(
    isolated_runtime,
    monkeypatch,
) -> None:
    visible_runs = importlib.import_module("apps.api.jarvis_api.services.visible_runs")
    visible_runs = importlib.reload(visible_runs)
    visible_model = importlib.import_module("apps.api.jarvis_api.services.visible_model")

    chunks, last_use = _run_visible_stream(
        visible_runs=visible_runs,
        visible_model=visible_model,
        monkeypatch=monkeypatch,
        text=(
            '<capability-call id="tool:read-workspace-user-profile" /> '
            '<capability-call id="tool:read-repository-readme" /> '
            '<capability-call id="tool:read-workspace-user-profile" />'
        ),
        run_id="visible-cap-multi",
    )

    capability_events = _parse_sse(chunks, "capability")
    delta_events = _parse_sse(chunks, "delta")

    assert len(capability_events) == 1
    assert capability_events[0]["capability_id"] == "tool:read-workspace-user-profile"
    assert any("# USER" in str(item.get("delta") or "") for item in delta_events)
    assert all("<capability-call" not in str(item.get("delta") or "") for item in delta_events)
    assert last_use.get("capability_id") == "tool:read-workspace-user-profile"
