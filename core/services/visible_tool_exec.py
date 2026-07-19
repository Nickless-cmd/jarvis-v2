"""Shared tool-exec pump for the visible run (Boy-Scout extraction, 2026-07-19).

Both the first-pass and the agentic-loop tool-execution blocks in ``visible_runs.py``
were near-identical ~120-line pumps: announce each tool_call as a ``working_step``,
re-assert the load-bearing ContextVars (scope / session_id / owner-override) that do
NOT reliably survive the async-generator→executor boundary, snapshot the context, run
the batch in a worker thread (so a slow/hanging tool can't freeze the event loop), and
emit periodic heartbeats so a silent SSE window doesn't get the connection culled.

This helper IS that pump, as an async generator that YIELDS the working_step /
tool_call / heartbeat SSE strings and, on completion, fills ``out`` with the executed
result list + the updated step counter. The agentic-only reasoning-interceptor stays in
the caller (it may mutate the pending tool_calls before this runs).

Path B (``local_tool_exec``): when ``run.local_tool_exec`` is set, each announced call
is registered with ``local_tool_broker`` and emitted as a first-class ``tool_call``
event so the jarvis-code client runs it LOCALLY; the executor then WAITS on the broker
for the client's result instead of running the tool server-side. Default OFF → the
legacy server-side ``_execute_simple_tool_calls`` path is byte-identical to before.

Kept standalone: all imports from ``visible_runs`` are lazy (inside the function) so the
module-level ``from core.services.visible_tool_exec import run_tool_batch`` in
visible_runs.py does not create an import cycle.
"""
from __future__ import annotations

import asyncio
import contextvars as _ctxvars
import time
from typing import AsyncIterator


async def run_tool_batch(
    tool_calls: list[dict],
    *,
    run,
    loop,
    tool_scope: str,
    step_counter: int,
    heartbeat_interval_s: float,
    heartbeat_phase: str,
    out: dict,
    heartbeat_extra: dict | None = None,
    exec_start: float | None = None,
) -> AsyncIterator[str]:
    """Announce → execute → heartbeat pump for one tool batch.

    Yields the SSE strings (working_step, tool_call [Path B only], heartbeat). On
    completion fills ``out`` with ``{"results": [...], "step_counter": int}``.

    Args:
        tool_calls: the round's native tool_calls (already possibly held/emptied by
            the caller's reasoning interceptor).
        run: the VisibleRun (reads run_id / session_id / autonomous / local_tool_exec).
        loop: the running event loop (executor is offloaded there).
        tool_scope: re-asserted into the ContextVars before copy_context.
        step_counter: current working-step counter; incremented per announced call.
        heartbeat_interval_s: 5.0 first-pass / 15.0 agentic — the silent-window beat.
        heartbeat_phase: "first_pass_tools" / "agentic_tools" — the heartbeat phase tag.
        out: mutable dict the helper fills with results + updated step_counter.
        heartbeat_extra: extra heartbeat fields (e.g. {"round": n}); inserted BEFORE
            elapsed_s/beat so the wire JSON key-order matches the pre-extraction blocks.
        exec_start: monotonic reference for elapsed_s (agentic passes its own start so
            the end-logger matches); None → captured right before the executor task.
    """
    from core.services.visible_runs import (
        _sse, _parse_tc_args, _tool_label, touch_active_visible_run,
    )
    from core.services.simple_tool_executor import (
        _execute_simple_tool_calls, _execute_local_tool_calls,
    )

    _local = bool(getattr(run, "local_tool_exec", False))

    # ── Announce loop: one working_step per named call (+ Path B register/emit) ──
    for _tc in tool_calls:
        _tc_name = str((_tc.get("function") or {}).get("name") or _tc.get("name") or "")
        if _tc_name:
            step_counter += 1
            _tc_args = _parse_tc_args(_tc)
            yield _sse("working_step", {
                "type": "working_step",
                "run_id": run.run_id,
                "action": _tc_name,
                "detail": _tool_label(_tc_name, _tc_args),
                "step": step_counter,
                "status": "running",
            })
            if _local:
                # Path B: register the pending call BEFORE the executor waits on it
                # (race-safe: register precedes wait) and hand it to the local
                # jarvis-code client as a first-class tool_call event. The client runs
                # it and POSTs the result to /chat/tool_results → broker.resolve.
                _call_id = str(_tc.get("id") or "")
                try:
                    from core.services import local_tool_broker
                    local_tool_broker.register(
                        _call_id,
                        session_id=getattr(run, "session_id", "") or "",
                        name=_tc_name,
                    )
                except Exception:
                    pass
                yield _sse("tool_call", {
                    "type": "tool_call",
                    "run_id": run.run_id,
                    "session_id": getattr(run, "session_id", "") or "",
                    "call_id": _call_id,
                    "name": _tc_name,
                    "arguments": _tc_args,
                })

    # ── Re-assert load-bearing ContextVars BEFORE copy_context (VERBATIM) ──
    # loop.run_in_executor does NOT propagate ContextVars to the worker thread; and
    # scope/session_id do NOT reliably survive to this point across the async-generator
    # boundary (role/user_id do, scope does not). Without re-asserting from the known
    # run scope + session_id + refreshing the owner-override, execute_tool's role/scope
    # gate denies operator_* mid-run ("3-4 calls then block"). See the original comments
    # in visible_runs.py (~1879-1931 / ~3810-3836) for the full incident history.
    if tool_scope:
        try:
            from core.tools.tool_scoping import set_tool_scope as _reassert_scope
            _reassert_scope(tool_scope)
        except Exception:
            pass
    try:
        from core.identity.workspace_context import set_session_id as _set_sid
        if getattr(run, "session_id", ""):
            _set_sid(run.session_id)
    except Exception:
        pass
    try:
        from core.services import override_store as _ovs
        if getattr(run, "session_id", "") and _ovs.is_active(run.session_id):
            _ovs.touch(run.session_id)
    except Exception:
        pass
    _ctx_for_exec = _ctxvars.copy_context()

    # ── Run the batch in a worker thread (never freeze the event loop) ──
    # Path B substitutes only the invocation: _execute_local_tool_calls waits on the
    # broker for the client's result; the prep/finalize (dedup/cache/gate/format) and
    # the run_in_executor + heartbeat scaffolding are unchanged.
    _exec_fn = _execute_local_tool_calls if _local else _execute_simple_tool_calls

    async def _await_tools() -> list[dict]:
        return await loop.run_in_executor(
            None,
            lambda: _ctx_for_exec.run(
                _exec_fn,
                tool_calls,
                force=run.autonomous,
                run_id=run.run_id,
                session_id=run.session_id,
                user_message=run.user_message,
            ),
        )

    _tool_task = asyncio.ensure_future(_await_tools())
    _start = exec_start if exec_start is not None else time.monotonic()
    _beats = 0
    while not _tool_task.done():
        try:
            await asyncio.wait_for(asyncio.shield(_tool_task), timeout=heartbeat_interval_s)
        except asyncio.TimeoutError:
            # Tools still running — keep the stream alive + touch cross-process liveness.
            _beats += 1
            try:
                touch_active_visible_run(run.run_id)
            except Exception:
                pass
            _hb: dict = {
                "type": "heartbeat",
                "run_id": run.run_id,
                "phase": heartbeat_phase,
            }
            if heartbeat_extra:
                _hb.update(heartbeat_extra)
            _hb["elapsed_s"] = int(time.monotonic() - _start)
            _hb["beat"] = _beats
            yield _sse("heartbeat", _hb)
    _results = await _tool_task

    out["results"] = _results
    out["step_counter"] = step_counter
