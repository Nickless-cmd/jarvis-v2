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
