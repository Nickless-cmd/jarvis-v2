from __future__ import annotations

import importlib
import json
from pathlib import Path


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
    second_pass_text: str | list[str] | None = None,
    user_message: str = "smoke",
    stream_error: Exception | None = None,
    second_pass_error: Exception | None = None,
) -> tuple[list[str], dict[str, object]]:
    monkeypatch.setattr(visible_runs, "record_cost", lambda **kwargs: None)
    monkeypatch.setattr(
        visible_runs, "_track_runtime_candidates", lambda run, assistant_text: None
    )
    monkeypatch.setattr(
        visible_runs, "_persist_session_assistant_message", lambda run, message: None
    )
    monkeypatch.setattr(visible_runs, "append_chat_message", lambda **kwargs: {})

    def stub_stream_visible_model(**kwargs):
        if stream_error is not None:
            raise stream_error
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
    second_pass_calls: list[str] = []

    def stub_execute_visible_model(*, message: str, provider: str, model: str, session_id=None):
        second_pass_calls.append(message)
        if second_pass_error is not None:
            raise second_pass_error
        if isinstance(second_pass_text, list):
            response_text = second_pass_text.pop(0) if second_pass_text else "Grounded fallback response."
        else:
            response_text = second_pass_text or "Grounded fallback response."
        return visible_model.VisibleModelResult(
            text=response_text,
            input_tokens=2,
            output_tokens=3,
            cost_usd=0.0,
        )

    monkeypatch.setattr(visible_runs, "execute_visible_model", stub_execute_visible_model)

    run = visible_runs.VisibleRun(
        run_id=run_id,
        lane="local",
        provider="phase1-runtime",
        model="stub",
        user_message=user_message,
        session_id="session-smoke",
    )

    async def collect() -> list[str]:
        chunks: list[str] = []
        async for chunk in visible_runs._stream_visible_run(run):
            chunks.append(chunk)
        return chunks

    import asyncio

    chunks = asyncio.run(collect())
    last_use = visible_runs.get_last_visible_capability_use() or {}
    last_trace = visible_runs.get_last_visible_execution_trace() or {}
    return chunks, {**last_use, "second_pass_calls": second_pass_calls, "trace": last_trace}


def test_visible_run_executes_read_capability_and_surfaces_result(
    isolated_runtime,
    monkeypatch,
) -> None:
    visible_runs = importlib.import_module("core.services.visible_runs")
    visible_runs = importlib.reload(visible_runs)
    visible_model = importlib.import_module("core.services.visible_model")
    chunks, last_use = _run_visible_stream(
        visible_runs=visible_runs,
        visible_model=visible_model,
        monkeypatch=monkeypatch,
        text='<capability-call id="tool:read-workspace-user-profile" />',
        run_id="visible-cap-read",
        second_pass_text="Bjørn er angivet som primary user, og relationen er co-development.",
    )

    capability_events = _parse_sse(chunks, "capability")
    delta_events = _parse_sse(chunks, "delta")

    assert capability_events
    assert capability_events[-1]["capability_id"] == "tool:read-workspace-user-profile"
    assert capability_events[-1]["status"] == "executed"
    assert capability_events[-1]["execution_mode"] == "workspace-file-read"
    assert any(
        "Bjørn er angivet som primary user" in str(item.get("delta") or "")
        for item in delta_events
    )
    assert last_use.get("capability_id") == "tool:read-workspace-user-profile"
    assert last_use.get("status") == "executed"
    assert len(last_use.get("second_pass_calls") or []) == 1


def test_visible_run_surfaces_gated_write_capability_without_execution(
    isolated_runtime,
    monkeypatch,
) -> None:
    visible_runs = importlib.import_module("core.services.visible_runs")
    visible_runs = importlib.reload(visible_runs)
    visible_model = importlib.import_module("core.services.visible_model")
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
    assert last_use.get("second_pass_calls") == []


def test_visible_run_consumes_prose_plus_capability_without_raw_tag_leakage(
    isolated_runtime,
    monkeypatch,
) -> None:
    visible_runs = importlib.import_module("core.services.visible_runs")
    visible_runs = importlib.reload(visible_runs)
    visible_model = importlib.import_module("core.services.visible_model")

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
        second_pass_text="Profilen viser, at Bjørn er primary user i et co-development setup.",
    )

    capability_events = _parse_sse(chunks, "capability")
    delta_events = _parse_sse(chunks, "delta")

    assert capability_events
    assert capability_events[-1]["capability_id"] == "tool:read-workspace-user-profile"
    assert any("Profilen viser" in str(item.get("delta") or "") for item in delta_events)
    assert all("<capability-call" not in str(item.get("delta") or "") for item in delta_events)
    assert last_use.get("capability_id") == "tool:read-workspace-user-profile"


def test_visible_run_executes_all_known_capabilities_when_multiple_are_emitted(
    isolated_runtime,
    monkeypatch,
) -> None:
    """All unique known capabilities execute; duplicates are deduped."""
    visible_runs = importlib.import_module("core.services.visible_runs")
    visible_runs = importlib.reload(visible_runs)
    visible_model = importlib.import_module("core.services.visible_model")

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
        second_pass_text="Jeg fandt brugerprofilen og readme og bruger dem som grundlag for svaret.",
    )

    capability_events = _parse_sse(chunks, "capability")
    delta_events = _parse_sse(chunks, "delta")

    # Both unique capabilities execute (third is deduped)
    assert len(capability_events) == 2
    executed_ids = [e["capability_id"] for e in capability_events]
    assert "tool:read-workspace-user-profile" in executed_ids
    assert "tool:read-repository-readme" in executed_ids
    assert any("brugerprofilen og readme" in str(item.get("delta") or "") for item in delta_events)
    assert all("<capability-call" not in str(item.get("delta") or "") for item in delta_events)
    assert len(last_use.get("second_pass_calls") or []) == 1


def test_visible_run_second_pass_strips_capability_markup_and_does_not_loop(
    isolated_runtime,
    monkeypatch,
) -> None:
    visible_runs = importlib.import_module("core.services.visible_runs")
    visible_runs = importlib.reload(visible_runs)
    visible_model = importlib.import_module("core.services.visible_model")

    chunks, last_use = _run_visible_stream(
        visible_runs=visible_runs,
        visible_model=visible_model,
        monkeypatch=monkeypatch,
        text='<capability-call id="tool:read-workspace-user-profile" />',
        run_id="visible-cap-second-pass-loop-stop",
        second_pass_text=[
            (
                'Jeg svarer nu grounded. '
                '<capability-call id="tool:read-repository-readme" />'
            ),
            "Grounded fallback response.",
        ],
    )

    capability_events = _parse_sse(chunks, "capability")
    delta_events = _parse_sse(chunks, "delta")

    assert len(capability_events) == 2
    assert capability_events[0]["capability_id"] == "tool:read-workspace-user-profile"
    assert capability_events[1]["capability_id"] == "tool:read-repository-readme"


def test_visible_run_native_tool_calls_use_visible_followup_dispatcher(
    isolated_runtime,
    monkeypatch,
) -> None:
    visible_runs = importlib.import_module("core.services.visible_runs")
    visible_runs = importlib.reload(visible_runs)
    visible_model = importlib.import_module("core.services.visible_model")
    visible_followup = importlib.import_module("core.services.visible_followup")
    ollama_prompt = importlib.import_module("core.services.ollama_visible_prompt")

    monkeypatch.setattr(visible_runs, "record_cost", lambda **kwargs: None)
    monkeypatch.setattr(
        visible_runs, "_track_runtime_candidates", lambda run, assistant_text: None
    )
    monkeypatch.setattr(
        visible_runs, "_persist_session_assistant_message", lambda run, message: None
    )
    monkeypatch.setattr(visible_runs, "append_chat_message", lambda **kwargs: {})

    def stub_stream_visible_model(**kwargs):
        yield visible_model.VisibleModelToolCalls(
            tool_calls=[
                {
                    "id": "call-1",
                    "type": "function",
                    "function": {"name": "read_file", "arguments": {"path": "README.md"}},
                }
            ]
        )
        yield visible_model.VisibleModelStreamDone(
            result=visible_model.VisibleModelResult(
                text="",
                input_tokens=2,
                output_tokens=2,
                cost_usd=0.0,
            )
        )

    monkeypatch.setattr(visible_runs, "stream_visible_model", stub_stream_visible_model)
    monkeypatch.setattr(
        visible_runs,
        "_build_visible_input",
        lambda message, session_id=None, **_kwargs: [{"role": "user", "content": message}],
    )
    monkeypatch.setattr(
        ollama_prompt,
        "serialize_ollama_chat_messages",
        lambda payload: list(payload),
    )

    tool_exec_calls: list[list[dict]] = []

    def stub_execute_simple_tool_calls(tool_calls, *, force=False, run_id=None, **_kwargs):
        tool_exec_calls.append(list(tool_calls))
        if len(tool_exec_calls) == 1:
            return [
                {
                    "tool_name": "read_file",
                    "arguments": {"path": "README.md"},
                    "result": {"status": "ok", "text": "README content"},
                    "result_text": "README content",
                    "status": "ok",
                }
            ]
        # Intentionally return fewer results than requested tool calls
        # to ensure visible_runs still emits one tool-result per tool_call_id
        # when building followup exchanges.
        return [
            {
                "tool_name": "search_memory",
                "arguments": {"query": "jarvis"},
                "result": {"status": "ok", "text": "memory hit"},
                "result_text": "memory hit",
                "status": "ok",
            }
        ]

    monkeypatch.setattr(visible_runs, "_execute_simple_tool_calls", stub_execute_simple_tool_calls)

    followup_calls: list[dict[str, object]] = []

    def stub_stream_visible_followup(
        *,
        provider: str,
        model: str,
        base_messages: list[dict],
        exchanges: list,
        tool_definitions=None,
        round_index: int = 0,
        **_kwargs,
    ):
        followup_calls.append(
            {
                "provider": provider,
                "model": model,
                "round_index": round_index,
                "exchange_count": len(exchanges),
                "last_tool_calls": len(exchanges[-1].tool_calls) if exchanges else 0,
                "last_results": len(exchanges[-1].results) if exchanges else 0,
            }
        )
        if round_index == 0:
            yield visible_followup.FollowupToolCalls(
                tool_calls=[
                    {
                        "id": "call-2",
                        "type": "function",
                        "function": {
                            "name": "search_memory",
                            "arguments": {"query": "jarvis"},
                        },
                    },
                    {
                        "id": "call-3",
                        "type": "function",
                        "function": {
                            "name": "read_file",
                            "arguments": {"path": "README.md"},
                        },
                    }
                ]
            )
            yield visible_followup.FollowupDone(text="")
            return
        yield visible_followup.FollowupDelta(delta="Faerdigt svar fra followup.")
        yield visible_followup.FollowupDone(text="Faerdigt svar fra followup.")

    monkeypatch.setattr(
        visible_followup,
        "stream_visible_followup",
        stub_stream_visible_followup,
    )

    run = visible_runs.VisibleRun(
        run_id="visible-native-followup",
        lane="visible",
        provider="github-copilot",
        model="gpt-4o-mini",
        user_message="kør native tools",
        session_id="session-native-followup",
    )

    async def collect() -> list[str]:
        chunks: list[str] = []
        async for chunk in visible_runs._stream_visible_run(run):
            chunks.append(chunk)
        return chunks

    import asyncio

    chunks = asyncio.run(collect())
    delta_events = _parse_sse(chunks, "delta")
    done_events = _parse_sse(chunks, "done")

    assert any(
        "Faerdigt svar fra followup." in str(item.get("delta") or "")
        for item in delta_events
    )
    assert done_events
    assert len(followup_calls) >= 2
    assert followup_calls[0]["provider"] == "github-copilot"
    assert followup_calls[0]["exchange_count"] == 1
    assert followup_calls[1]["exchange_count"] == 2
    assert followup_calls[1]["last_tool_calls"] == 2
    assert followup_calls[1]["last_results"] == 2
    assert len(tool_exec_calls) == 2
    assert tool_exec_calls[1][0]["function"]["name"] == "search_memory"


def test_visible_run_executes_dynamic_external_read_from_user_message_path(
    isolated_runtime,
    monkeypatch,
    tmp_path: Path,
) -> None:
    visible_runs = importlib.import_module("core.services.visible_runs")
    visible_runs = importlib.reload(visible_runs)
    visible_model = importlib.import_module("core.services.visible_model")

    external_file = tmp_path / "external-visible-target.txt"
    external_file.write_text("Visible external read text.\n", encoding="utf-8")

    chunks, last_use = _run_visible_stream(
        visible_runs=visible_runs,
        visible_model=visible_model,
        monkeypatch=monkeypatch,
        text='<capability-call id="tool:read-external-file-by-path" />',
        run_id="visible-cap-external-read",
        second_pass_text="Jeg har læst den eksterne fil, og den indeholder Visible external read text.",
        user_message=f"Læs venligst {external_file}",
    )

    capability_events = _parse_sse(chunks, "capability")
    delta_events = _parse_sse(chunks, "delta")

    assert capability_events
    assert capability_events[-1]["capability_id"] == "tool:read-external-file-by-path"
    assert capability_events[-1]["status"] == "executed"
    assert capability_events[-1]["execution_mode"] == "external-file-read"
    assert any("Visible external read text." in str(item.get("delta") or "") for item in delta_events)
    assert all("<capability-call" not in str(item.get("delta") or "") for item in delta_events)
    assert last_use.get("capability_id") == "tool:read-external-file-by-path"
    assert len(last_use.get("second_pass_calls") or []) == 1


def test_visible_run_binds_external_read_target_from_capability_tag_attributes(
    isolated_runtime,
    monkeypatch,
    tmp_path: Path,
) -> None:
    visible_runs = importlib.import_module("core.services.visible_runs")
    visible_runs = importlib.reload(visible_runs)
    visible_model = importlib.import_module("core.services.visible_model")

    external_file = tmp_path / "external-visible-attr.txt"
    external_file.write_text("External attr binding text.\n", encoding="utf-8")

    chunks, last_use = _run_visible_stream(
        visible_runs=visible_runs,
        visible_model=visible_model,
        monkeypatch=monkeypatch,
        text=f'<capability-call id="tool:read-external-file-by-path" target_path="{external_file}" />',
        run_id="visible-cap-external-read-attr",
        second_pass_text="Jeg læste den eksplicit bundne eksterne fil.",
        user_message="ja tak",
    )

    capability_events = _parse_sse(chunks, "capability")
    trace_events = _parse_sse(chunks, "trace")

    assert capability_events
    assert capability_events[-1]["status"] == "executed"
    assert last_use.get("argument_source") == "tag-attributes"
    assert (last_use.get("parsed_arguments") or {}).get("target_path") == str(external_file)
    assert (last_use.get("trace") or {}).get("parsed_target_path") == str(external_file)
    assert trace_events
    assert trace_events[-1]["provider_second_pass_status"] == "completed"


def test_visible_run_executes_non_destructive_command_from_user_message(
    isolated_runtime,
    monkeypatch,
) -> None:
    visible_runs = importlib.import_module("core.services.visible_runs")
    visible_runs = importlib.reload(visible_runs)
    visible_model = importlib.import_module("core.services.visible_model")

    chunks, last_use = _run_visible_stream(
        visible_runs=visible_runs,
        visible_model=visible_model,
        monkeypatch=monkeypatch,
        text='<capability-call id="tool:run-non-destructive-command" />',
        run_id="visible-cap-non-destructive-exec",
        second_pass_text="Kommandoen kørte, og outputtet viser den aktuelle arbejdsmappe.",
        user_message="Kør `pwd` for at inspicere den aktuelle arbejdsmappe.",
    )

    capability_events = _parse_sse(chunks, "capability")
    delta_events = _parse_sse(chunks, "delta")

    assert capability_events
    assert capability_events[-1]["capability_id"] == "tool:run-non-destructive-command"
    assert capability_events[-1]["status"] == "executed"
    assert capability_events[-1]["execution_mode"] == "non-destructive-exec"
    assert any("aktuelle arbejdsmappe" in str(item.get("delta") or "") for item in delta_events)
    assert last_use.get("capability_id") == "tool:run-non-destructive-command"
    assert (last_use.get("trace") or {}).get("argument_source") == "user-message-fallback"
    assert len(last_use.get("second_pass_calls") or []) == 1


def test_visible_run_binds_exec_command_from_capability_tag_attributes(
    isolated_runtime,
    monkeypatch,
) -> None:
    visible_runs = importlib.import_module("core.services.visible_runs")
    visible_runs = importlib.reload(visible_runs)
    visible_model = importlib.import_module("core.services.visible_model")

    chunks, last_use = _run_visible_stream(
        visible_runs=visible_runs,
        visible_model=visible_model,
        monkeypatch=monkeypatch,
        text='<capability-call id="tool:run-non-destructive-command" command_text="pwd" />',
        run_id="visible-cap-exec-attr",
        second_pass_text="Jeg kørte den eksplicit bundne kommando og læste outputtet.",
        user_message="ja tak",
    )

    capability_events = _parse_sse(chunks, "capability")
    trace_events = _parse_sse(chunks, "trace")

    assert capability_events
    assert capability_events[-1]["status"] == "executed"
    assert last_use.get("argument_source") == "tag-attributes"
    assert (last_use.get("parsed_arguments") or {}).get("command_text") == "pwd"
    assert (last_use.get("trace") or {}).get("parsed_command_text") == "pwd"
    assert trace_events
    assert trace_events[-1]["selected_capability_id"] == "tool:run-non-destructive-command"


def test_visible_run_surfaces_exec_path_normalization_in_trace(
    isolated_runtime,
    monkeypatch,
) -> None:
    visible_runs = importlib.import_module("core.services.visible_runs")
    visible_runs = importlib.reload(visible_runs)
    visible_model = importlib.import_module("core.services.visible_model")

    chunks, last_use = _run_visible_stream(
        visible_runs=visible_runs,
        visible_model=visible_model,
        monkeypatch=monkeypatch,
        text='<capability-call id="tool:run-non-destructive-command" command_text="ls -la ~" />',
        run_id="visible-cap-exec-home-normalization",
        second_pass_text="Jeg normaliserede hjemmesti-argumentet og viste resultatet.",
        user_message="ja tak",
    )

    capability_events = _parse_sse(chunks, "capability")
    trace_events = _parse_sse(chunks, "trace")

    assert capability_events
    assert capability_events[-1]["status"] == "executed"
    assert trace_events
    assert trace_events[-1]["parsed_command_text"] == "ls -la ~"
    assert trace_events[-1]["normalized_command_text"] == f"ls -la {Path.home()}"
    assert trace_events[-1]["path_normalization_applied"] is True
    assert trace_events[-1]["normalization_source"] == "tilde"
    assert (last_use.get("trace") or {}).get("normalized_command_text") == f"ls -la {Path.home()}"


def test_visible_run_surfaces_sudo_exec_as_approval_gated_proposal_without_markup_leakage(
    isolated_runtime,
    monkeypatch,
) -> None:
    visible_runs = importlib.import_module("core.services.visible_runs")
    visible_runs = importlib.reload(visible_runs)
    visible_model = importlib.import_module("core.services.visible_model")

    chunks, last_use = _run_visible_stream(
        visible_runs=visible_runs,
        visible_model=visible_model,
        monkeypatch=monkeypatch,
        text='<capability-call id="tool:run-non-destructive-command" />',
        run_id="visible-cap-blocked-exec",
        user_message="Kør `sudo ls /root` og vis outputtet.",
    )

    capability_events = _parse_sse(chunks, "capability")
    delta_events = _parse_sse(chunks, "delta")

    assert capability_events
    assert capability_events[-1]["capability_id"] == "tool:run-non-destructive-command"
    assert capability_events[-1]["status"] == "approval-required"
    assert capability_events[-1]["execution_mode"] == "sudo-exec-proposal"
    assert any("approval-gated proposal only" in str(item.get("delta") or "") for item in delta_events)
    assert all("<capability-call" not in str(item.get("delta") or "") for item in delta_events)
    assert (last_use.get("trace") or {}).get("blocked_reason")
    assert last_use.get("second_pass_calls") == []


def test_visible_run_surfaces_mutating_exec_as_proposal_only(
    isolated_runtime,
    monkeypatch,
) -> None:
    visible_runs = importlib.import_module("core.services.visible_runs")
    visible_runs = importlib.reload(visible_runs)
    visible_model = importlib.import_module("core.services.visible_model")

    chunks, last_use = _run_visible_stream(
        visible_runs=visible_runs,
        visible_model=visible_model,
        monkeypatch=monkeypatch,
        text='<capability-call id="tool:run-non-destructive-command" command_text="git add README.md" />',
        run_id="visible-cap-mutating-exec-proposal",
        user_message="ja tak",
    )

    capability_events = _parse_sse(chunks, "capability")
    delta_events = _parse_sse(chunks, "delta")

    assert capability_events
    assert capability_events[-1]["status"] == "approval-required"
    assert capability_events[-1]["execution_mode"] == "mutating-exec-proposal"
    assert any("repo stewardship proposal only" in str(item.get("delta") or "") or "git-stage" in str(item.get("delta") or "") for item in delta_events)
    assert last_use.get("argument_source") == "tag-attributes"
    assert (last_use.get("trace") or {}).get("parsed_command_text") == "git add README.md"
    assert "git-stage" in str(last_use.get("detail") or "")
    assert last_use.get("second_pass_calls") == []


def test_visible_run_allows_bounded_git_status_as_non_destructive_exec(
    isolated_runtime,
    monkeypatch,
) -> None:
    visible_runs = importlib.import_module("core.services.visible_runs")
    visible_runs = importlib.reload(visible_runs)
    visible_model = importlib.import_module("core.services.visible_model")

    chunks, last_use = _run_visible_stream(
        visible_runs=visible_runs,
        visible_model=visible_model,
        monkeypatch=monkeypatch,
        text='<capability-call id="tool:run-non-destructive-command" command_text="git status" />',
        run_id="visible-cap-git-status",
        second_pass_text="Jeg læste git-status som bounded inspection og summerede den.",
        user_message="ja tak",
    )

    capability_events = _parse_sse(chunks, "capability")
    delta_events = _parse_sse(chunks, "delta")

    assert capability_events
    assert capability_events[-1]["status"] == "executed"
    assert capability_events[-1]["execution_mode"] == "non-destructive-exec"
    assert any("git-status" in str(item.get("delta") or "") or "bounded inspection" in str(item.get("delta") or "") for item in delta_events)
    assert (last_use.get("parsed_arguments") or {}).get("command_text") == "git status"


def test_visible_run_surfaces_provider_first_pass_error_in_trace(
    isolated_runtime,
    monkeypatch,
) -> None:
    visible_runs = importlib.import_module("core.services.visible_runs")
    visible_runs = importlib.reload(visible_runs)
    visible_model = importlib.import_module("core.services.visible_model")

    chunks, last_use = _run_visible_stream(
        visible_runs=visible_runs,
        visible_model=visible_model,
        monkeypatch=monkeypatch,
        text="",
        run_id="visible-cap-provider-first-pass-error",
        stream_error=RuntimeError("Ollama visible execution returned no streamed response"),
    )

    failed_events = _parse_sse(chunks, "failed")
    trace_events = _parse_sse(chunks, "trace")

    assert failed_events
    assert "first-pass-provider-error" in str(failed_events[-1].get("error") or "")
    assert trace_events
    assert trace_events[-1]["provider_first_pass_status"] == "failed"
    assert trace_events[-1]["invoke_status"] == "not-invoked"
    assert "no streamed response" in str(trace_events[-1].get("provider_error_summary") or "")


# ---------------------------------------------------------------------------
# Multi-capability extraction tests
# ---------------------------------------------------------------------------


def test_extract_capability_plan_returns_all_known_capabilities() -> None:
    """_extract_capability_plan must return all known capabilities, not just the first."""
    visible_runs = importlib.import_module("core.services.visible_runs")
    visible_runs = importlib.reload(visible_runs)

    text = (
        '<capability-call id="tool:read-workspace-user-profile" /> '
        '<capability-call id="tool:read-repository-readme" /> '
        '<capability-call id="tool:read-workspace-user-profile" />'
    )
    plan = visible_runs._extract_capability_plan(text)

    assert plan["selected_capability_id"] == "tool:read-workspace-user-profile"
    assert plan["had_markup"] is True
    assert plan["multiple"] is True
    all_caps = plan["all_capabilities"]
    assert len(all_caps) == 2  # deduped: user-profile + readme
    cap_ids = [c["capability_id"] for c in all_caps]
    assert "tool:read-workspace-user-profile" in cap_ids
    assert "tool:read-repository-readme" in cap_ids


def test_extract_capability_plan_caps_at_max_capabilities() -> None:
    """_extract_capability_plan must not return more than _MAX_CAPABILITIES_PER_TURN."""
    visible_runs = importlib.import_module("core.services.visible_runs")
    visible_runs = importlib.reload(visible_runs)

    # All tags have same ID so dedup means only 1 entry, but the cap logic is exercised
    tags = " ".join(
        f'<capability-call id="tool:read-workspace-user-profile" target_path="/fake/{i}" />'
        for i in range(10)
    )
    plan = visible_runs._extract_capability_plan(tags)
    assert len(plan["all_capabilities"]) <= visible_runs._MAX_CAPABILITIES_PER_TURN


def test_extract_capability_plan_keeps_multiple_block_capabilities_in_order() -> None:
    visible_runs = importlib.import_module("core.services.visible_runs")
    visible_runs = importlib.reload(visible_runs)

    text = """
<capability-call id="tool:read-workspace-user-profile">
ignored block content
</capability-call>
<capability-call id="tool:read-repository-readme">
more ignored block content
</capability-call>
"""
    plan = visible_runs._extract_capability_plan(text)

    assert plan["selected_capability_id"] == "tool:read-workspace-user-profile"
    assert plan["multiple"] is True
    assert [c["capability_id"] for c in plan["all_capabilities"]] == [
        "tool:read-workspace-user-profile",
        "tool:read-repository-readme",
    ]


def test_extract_capability_plan_keeps_mixed_block_and_self_closing_calls() -> None:
    visible_runs = importlib.import_module("core.services.visible_runs")
    visible_runs = importlib.reload(visible_runs)

    text = """
<capability-call id="tool:run-non-destructive-command" command_text="lscpu" />
<capability-call id="tool:read-repository-readme">
ignored block content
</capability-call>
<capability-call id="tool:run-non-destructive-command" command_text="free -h" />
"""
    plan = visible_runs._extract_capability_plan(text)

    assert plan["multiple"] is True
    assert [c["capability_id"] for c in plan["all_capabilities"]] == [
        "tool:run-non-destructive-command",
        "tool:read-repository-readme",
        "tool:run-non-destructive-command",
    ]
    assert plan["selected_arguments"]["command_text"] == "lscpu"
    assert plan["all_capabilities"][2]["arguments"]["command_text"] == "free -h"


# ---------------------------------------------------------------------------
# Multi-capability execution tests
# ---------------------------------------------------------------------------


def test_visible_run_executes_all_capabilities_not_just_first(
    isolated_runtime,
    monkeypatch,
) -> None:
    """When LLM emits multiple capability tags, ALL known capabilities must execute."""
    visible_runs = importlib.import_module("core.services.visible_runs")
    visible_runs = importlib.reload(visible_runs)
    visible_model = importlib.import_module("core.services.visible_model")

    # Use two capabilities that are always present in the isolated workspace
    chunks, last_use = _run_visible_stream(
        visible_runs=visible_runs,
        visible_model=visible_model,
        monkeypatch=monkeypatch,
        text=(
            '<capability-call id="tool:read-workspace-user-profile" /> '
            '<capability-call id="tool:read-repository-readme" />'
        ),
        run_id="visible-cap-multi-exec",
        second_pass_text="Profilen og readme er begge læst.",
    )

    capability_events = _parse_sse(chunks, "capability")
    delta_events = _parse_sse(chunks, "delta")

    # Both capabilities must have been executed
    assert len(capability_events) == 2
    executed_ids = [e["capability_id"] for e in capability_events]
    assert "tool:read-workspace-user-profile" in executed_ids
    assert "tool:read-repository-readme" in executed_ids
    # Second pass must have been called with both results
    assert len(last_use.get("second_pass_calls") or []) == 1
    second_pass_msg = last_use["second_pass_calls"][0]
    assert "tool:read-workspace-user-profile" in second_pass_msg
    assert "tool:read-repository-readme" in second_pass_msg
    assert "Every substantive claim must be grounded" in second_pass_msg
    assert "If more read-only data is clearly needed" in second_pass_msg


def test_visible_run_allows_one_extra_autonomous_read_only_round(
    isolated_runtime,
    monkeypatch,
) -> None:
    visible_runs = importlib.import_module("core.services.visible_runs")
    visible_runs = importlib.reload(visible_runs)
    visible_model = importlib.import_module("core.services.visible_model")

    chunks, last_use = _run_visible_stream(
        visible_runs=visible_runs,
        visible_model=visible_model,
        monkeypatch=monkeypatch,
        text='<capability-call id="tool:read-workspace-user-profile" />',
        run_id="visible-cap-extra-round",
        user_message="Lav en kodeanalyse af main repo og fortsæt selv.",
        second_pass_text=[
            '<capability-call id="tool:read-repository-readme" />',
            "Jeg har nu læst både konkret kodekontekst og readme, og README alene var ikke nok.",
        ],
    )

    capability_events = _parse_sse(chunks, "capability")
    delta_events = _parse_sse(chunks, "delta")

    assert len(capability_events) == 2
    assert [e["capability_id"] for e in capability_events] == [
        "tool:read-workspace-user-profile",
        "tool:read-repository-readme",
    ]
    assert len(last_use.get("second_pass_calls") or []) == 2
    assert any("README alene var ikke nok" in str(item.get("delta") or "") for item in delta_events)


def test_visible_run_second_pass_treats_memory_write_as_normal_success(
    isolated_runtime,
    monkeypatch,
) -> None:
    visible_runs = importlib.import_module("core.services.visible_runs")
    visible_runs = importlib.reload(visible_runs)
    visible_model = importlib.import_module("core.services.visible_model")

    chunks, last_use = _run_visible_stream(
        visible_runs=visible_runs,
        visible_model=visible_model,
        monkeypatch=monkeypatch,
        text=(
            '<capability-call id="tool:write-workspace-memory">\n'
            '# MEMORY\nGem at /media/projects/jarvis-v2 er main repo.\n'
            '</capability-call>'
        ),
        run_id="visible-cap-memory-normalized",
        user_message="Husk dette: /media/projects/jarvis-v2 er main repo.",
        second_pass_text="Det er gemt i hukommelsen.",
    )

    second_pass_msg = (last_use.get("second_pass_calls") or [""])[0]
    assert "state that it has been saved" in second_pass_msg
    assert "Do not describe block syntax" in second_pass_msg
    delta_events = _parse_sse(chunks, "delta")
    assert any("gemt i hukommelsen" in str(item.get("delta") or "") for item in delta_events)
