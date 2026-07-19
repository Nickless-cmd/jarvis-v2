"""Native tool_calls executor (extracted from visible_runs.py, Boy-Scout 2026-07-08).

Executes a round's native tool_calls via simple_tools and returns result dicts.
Re-exported from visible_runs for backward compatibility.

Part C (tool concurrency): read-only rounds may execute concurrently. Only the
tool INVOCATION overlaps — dedup, cache, commit-gate and controller bookkeeping
stay single-threaded (prepare + finalize phases). Each parallel task runs inside
its own ``copy_context()`` so the mode/role/tier gating ContextVars
(``tool_scoping`` / ``workspace_context``, read inside ``execute_tool``) travel
to every worker thread. Default mode is off → byte-identical to the sequential
path until flipped.
"""
from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from contextvars import copy_context

from core.eventbus.bus import event_bus


def _prepare_call(tc, *, force, run_id, session_id, user_message, controller, round_seen):
    """Single-thread prep for one call: parse/stamp args, signature, dedup, cache,
    commit-gate. Returns ("result", result_dict) for a short-circuit (duplicate/
    cached/gate-blocked), ("skip", None) for a nameless call, or ("run", token)
    where token carries name/arguments/signature/soft_warn for the invoke+finalize
    phases. Never runs the tool."""
    fn = tc.get("function") or {}
    name = str(fn.get("name") or "")
    arguments = fn.get("arguments") or {}
    if isinstance(arguments, str):
        try:
            arguments = json.loads(arguments) if arguments.strip() else {}
        except (ValueError, TypeError):
            arguments = {}
    if not isinstance(arguments, dict):
        arguments = {}
    if not name:
        return ("skip", None)
    try:
        from core.services.in_flight_runs import mark_tool
        mark_tool(run_id or "", name)
    except Exception:
        pass
    arguments = dict(arguments)
    if session_id:
        arguments["_runtime_session_id"] = session_id
    if run_id:
        arguments["_runtime_turn_id"] = run_id
    try:
        from core.identity.workspace_context import current_user_id
        uid = current_user_id()
        if uid:
            arguments["_runtime_user_id"] = uid
    except Exception:
        pass
    if force or (controller and controller.trust_all):
        arguments["_runtime_trust_all"] = True
    signature = json.dumps({"tool_name": name, "arguments": arguments},
                           ensure_ascii=False, sort_keys=True)
    seen = (controller.seen_simple_tool_call_signatures if controller else set())
    if signature in seen or signature in round_seen:
        return ("result", {
            "tool_name": name, "arguments": arguments,
            "result": {"status": "duplicate_suppressed",
                       "message": "Skipped duplicate tool call in the same visible run."},
            "result_text": "[Duplicate tool call skipped in same visible run]",
            "status": "duplicate_suppressed"})
    try:
        from core.services.agentic_tool_cache import get_cached_result
        _cached = get_cached_result(name, arguments)
    except Exception:
        _cached = None
    if _cached:
        return ("result", {
            "tool_name": name, "arguments": arguments,
            "result": {"status": "ok", "cached": True, "stored_at": _cached.get("stored_at")},
            "result_text": str(_cached.get("result_text") or ""),
            "status": "ok", "cached": True})
    from core.services.commit_gate_arbiter import evaluate_commit_gates
    _cg = evaluate_commit_gates(name=name, arguments=arguments,
                                user_message=user_message,
                                session_id=session_id or "", run_id=run_id or "")
    if _cg.blocked:
        _gate_reason = _cg.reason or "Ukendt gate-blokering"
        _gate_type = _cg.gate_type or "decision_gate"
        try:
            event_bus.publish(f"{_gate_type}.blocked",
                              {"tool_name": name, "reason": _gate_reason[:500], "run_id": run_id})
        except Exception:
            pass
        return ("result", {
            "tool_name": name, "arguments": arguments,
            "result": {"status": "gate_blocked", "gate_type": _gate_type, "message": _gate_reason},
            "result_text": f"[{_gate_type}] {_gate_reason}", "status": "gate_blocked"})
    # Reserve the signature for within-round dedup (parallel: success unknown yet;
    # a same-round exact duplicate read is suppressed — benign for idempotent reads).
    round_seen.add(signature)
    return ("run", {"name": name, "arguments": arguments,
                    "signature": signature, "soft_warn": _cg.soft_warn})


def _finalize_call(token, raw_result, *, controller, exec_fmt):
    """Single-thread finalize for one executed call: soft-warn wrap, mark-seen on
    ok, cache-store, assemble the result dict. exec_fmt = format_tool_result_for_model."""
    name = token["name"]
    arguments = token["arguments"]
    signature = token["signature"]
    soft_warn = token["soft_warn"]
    result_text = exec_fmt(name, raw_result)
    if soft_warn:
        result_text = f"⚠ {soft_warn}\n\n{result_text}"
    if controller and raw_result.get("status") == "ok":
        controller.seen_simple_tool_call_signatures.add(signature)
    try:
        from core.services.agentic_tool_cache import store_result
        store_result(tool_name=name, arguments=arguments, result_text=result_text,
                     status=str(raw_result.get("status", "ok")))
    except Exception:
        pass
    return {"tool_name": name, "arguments": arguments, "result": raw_result,
            "result_text": result_text, "status": raw_result.get("status", "ok")}


def _execute_simple_tool_calls(
    tool_calls: list[dict],
    *,
    force: bool = False,
    run_id: str | None = None,
    session_id: str | None = None,
    user_message: str = "",
) -> list[dict[str, object]]:
    """Execute native tool_calls directly via simple_tools. Returns results.

    When *force* is True (autonomous runs), use ``execute_tool_force`` which
    bypasses the approval gate (blocked commands are still blocked).

    Pre-execution gates (veto + decision) run BEFORE each tool call. If either
    gate blocks, the tool is replaced with a gate-blocked result. Read-only rounds
    may run concurrently (mode-gated, default off) — see module docstring.
    """
    from core.services.visible_runs import get_visible_run_controller, _MAX_CAPABILITIES_PER_TURN
    from core.tools.simple_tools import execute_tool, execute_tool_force, format_tool_result_for_model
    from core.services.tool_concurrency import is_parallelizable, concurrency_mode, _MAX_CONCURRENCY

    _exec = execute_tool_force if force else execute_tool

    results: list[dict[str, object]] = []
    controller = get_visible_run_controller(run_id) if run_id else None
    calls = tool_calls[:_MAX_CAPABILITIES_PER_TURN]
    round_seen: set[str] = set()

    _parallel = False
    try:
        _parallel = is_parallelizable(calls, mode=concurrency_mode())
    except Exception:
        _parallel = False

    if not _parallel:
        # ── Sequential path (default; behaviour-identical to pre-Part-C) ──
        for tc in calls:
            kind, payload = _prepare_call(
                tc, force=force, run_id=run_id, session_id=session_id,
                user_message=user_message, controller=controller, round_seen=round_seen)
            if kind == "skip":
                continue
            if kind == "result":
                results.append(payload)
                continue
            raw = _exec(payload["name"], payload["arguments"])
            results.append(_finalize_call(payload, raw, controller=controller,
                                          exec_fmt=format_tool_result_for_model))
        return results

    # ── Parallel path (read-only rounds only) ──
    # Prepare all (single-thread, in order) → plan of (idx, kind, payload).
    plan: list[tuple[int, str, object]] = []
    for idx, tc in enumerate(calls):
        kind, payload = _prepare_call(
            tc, force=force, run_id=run_id, session_id=session_id,
            user_message=user_message, controller=controller, round_seen=round_seen)
        plan.append((idx, kind, payload))
    run_items = [(idx, p) for (idx, kind, p) in plan if kind == "run"]
    raw_by_idx: dict[int, dict] = {}
    if run_items:
        with ThreadPoolExecutor(max_workers=min(_MAX_CONCURRENCY, len(run_items))) as pool:
            fut_to_idx = {}
            for idx, p in run_items:
                # Per-task ContextVar snapshot: this thread already runs inside
                # _ctx_for_agentic_exec (correct role/scope/override). copy_context()
                # per task so each worker re-enters its OWN copy — a single Context
                # cannot be .run() concurrently from multiple threads.
                ctx_i = copy_context()
                fut = pool.submit(ctx_i.run, _exec, p["name"], p["arguments"])
                fut_to_idx[fut] = idx
            for fut in as_completed(fut_to_idx):
                idx = fut_to_idx[fut]
                try:
                    raw_by_idx[idx] = fut.result()
                except Exception as exc:
                    raw_by_idx[idx] = {"status": "error", "message": str(exc)}
    # Finalize in emission order (single-thread) → deterministic result list.
    for (idx, kind, payload) in plan:
        if kind == "skip":
            continue
        if kind == "result":
            results.append(payload)
            continue
        raw = raw_by_idx.get(idx) or {"status": "error", "message": "no result"}
        results.append(_finalize_call(payload, raw, controller=controller,
                                      exec_fmt=format_tool_result_for_model))
    # Observability: how often / how wide concurrency fired.
    try:
        from core.services import central_timeseries as _cts_conc
        _cts_conc.record("tool", "concurrency", float(len(run_items)),
                         meta={"run_id": run_id, "n": len(run_items),
                               "cap": _MAX_CONCURRENCY})
    except Exception:
        pass
    return results


def _execute_local_tool_calls(
    tool_calls: list[dict],
    *,
    force: bool = False,
    run_id: str | None = None,
    session_id: str | None = None,
    user_message: str = "",
) -> list[dict[str, object]]:
    """Path B (local_tool_exec) executor — server-owned transcript, CLIENT-side run.

    Byte-identical 5-key result shape as ``_execute_simple_tool_calls`` (tool_name,
    arguments, result, result_text, status). Reuses ``_prepare_call`` / ``_finalize_call``
    verbatim; ONLY the invocation step differs — instead of calling simple_tools
    server-side, it waits on ``local_tool_broker`` for the jarvis-code client to run the
    tool locally and POST the result back to ``/chat/tool_results``.

    Contract with the caller (``run_tool_batch``): every tool_call has already been
    ``local_tool_broker.register(...)``'d and emitted to the client BEFORE this runs, so
    the ``collect_results`` wait here is race-safe (register precedes wait).

    Phase-1 prep (dedup/cache/commit-gate) is identical to the server path. Only calls
    whose prep returns kind=="run" are collected from the broker; short-circuit results
    (dedup/cache/gate) fold in with no client roundtrip.
    """
    from core.services.visible_runs import get_visible_run_controller, _MAX_CAPABILITIES_PER_TURN
    from core.tools.simple_tools import format_tool_result_for_model
    from core.services import local_tool_broker

    results: list[dict[str, object]] = []
    controller = get_visible_run_controller(run_id) if run_id else None
    calls = tool_calls[:_MAX_CAPABILITIES_PER_TURN]
    round_seen: set[str] = set()

    # Phase 1: prep every call (single-thread, in order). Gather run-calls' call_ids
    # so the broker wait happens as one batch (client runs them concurrently).
    plan: list[tuple[str, object, str]] = []  # (kind, payload, call_id)
    run_call_ids: list[str] = []
    for tc in calls:
        call_id = str(tc.get("id") or "")
        kind, payload = _prepare_call(
            tc, force=force, run_id=run_id, session_id=session_id,
            user_message=user_message, controller=controller, round_seen=round_seen)
        plan.append((kind, payload, call_id))
        if kind == "run":
            run_call_ids.append(call_id)

    collected: dict[str, tuple[str | None, bool]] = {}
    if run_call_ids:
        collected = local_tool_broker.collect_results(run_call_ids)

    for kind, payload, call_id in plan:
        if kind == "skip":
            continue
        if kind == "result":
            results.append(payload)
            continue
        # kind == "run": fold in the client's local result via the broker.
        result_text, is_error = collected.get(call_id, (None, True))
        if is_error or result_text is None:
            # Timeout / unknown / client-reported error. format_tool_result_for_model
            # reads the "error" key for status=="error"; surface the client's message
            # (or a typed timeout placeholder) there so the model sees the real cause.
            raw: dict = {"status": "error",
                         "error": result_text or "[local tool timeout: no client result]"}
        else:
            # Success: the client's verbatim output text. format_tool_result_for_model
            # reads the "text" key for a non-error status → renders it as-is.
            raw = {"status": "ok", "text": result_text}
        results.append(_finalize_call(payload, raw, controller=controller,
                                      exec_fmt=format_tool_result_for_model))
    return results
