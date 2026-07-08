"""Native tool_calls executor (extracted from visible_runs.py, Boy-Scout 2026-07-08).

Executes a round's native tool_calls via simple_tools and returns result dicts.
Re-exported from visible_runs for backward compatibility. Part C adds an optional
concurrent path for read-only rounds (see _execute_simple_tool_calls)."""
from __future__ import annotations

import json

from core.eventbus.bus import event_bus


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

    Pre-execution gates (veto + decision) run BEFORE each tool call.
    If either gate blocks, the tool is replaced with a gate-blocked result
    that surfaces the conflict to the user for confirmation.
    """
    from core.services.visible_runs import get_visible_run_controller, _MAX_CAPABILITIES_PER_TURN
    from core.tools.simple_tools import execute_tool, execute_tool_force, format_tool_result_for_model

    _exec = execute_tool_force if force else execute_tool

    results: list[dict[str, object]] = []
    controller = get_visible_run_controller(run_id) if run_id else None
    for tc in tool_calls[:_MAX_CAPABILITIES_PER_TURN]:
        fn = tc.get("function") or {}
        name = str(fn.get("name") or "")
        arguments = fn.get("arguments") or {}
        # OpenAI-compat providers (Copilot, OpenCode, Groq, ...) serialize
        # tool_call arguments as a JSON string per the OpenAI wire spec.
        # Downstream executors expect a dict, so parse once here.
        if isinstance(arguments, str):
            try:
                arguments = json.loads(arguments) if arguments.strip() else {}
            except (ValueError, TypeError):
                arguments = {}
        if not isinstance(arguments, dict):
            arguments = {}
        if not name:
            continue
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
        # Stamp the active user_id from workspace context so operator_*
        # tools route to THIS user's JarvisX bridge — not owner_user_id
        # by default. Without this, Mikkel asking "open facebook" would
        # dispatch the open_url to Bjørn's bridge because _operator_user_id
        # in simple_tools falls back to owner via runtime.json. (The
        # message_user_attribution DB-lookup step in that fallback chain
        # is also empty — no code writes that table.)
        try:
            from core.identity.workspace_context import current_user_id
            uid = current_user_id()
            if uid:
                arguments["_runtime_user_id"] = uid
        except Exception:
            pass
        # Forward trust_all so operator_* tools can skip per-call approval
        # dialogs when the user already opted into "Trust All" mode.
        # `force=True` (autonomous runs) implies trust_all — no human in
        # the loop to approve anything.
        if force or (controller and controller.trust_all):
            arguments["_runtime_trust_all"] = True
        signature = json.dumps(
            {
                "tool_name": name,
                "arguments": arguments,
            },
            ensure_ascii=False,
            sort_keys=True,
        )
        if controller and signature in controller.seen_simple_tool_call_signatures:
            results.append({
                "tool_name": name,
                "arguments": arguments,
                "result": {
                    "status": "duplicate_suppressed",
                    "message": "Skipped duplicate tool call in the same visible run.",
                },
                "result_text": "[Duplicate tool call skipped in same visible run]",
                "status": "duplicate_suppressed",
            })
            continue

        try:
            from core.services.agentic_tool_cache import get_cached_result
            _cached = get_cached_result(name, arguments)
        except Exception:
            _cached = None
        if _cached:
            results.append({
                "tool_name": name,
                "arguments": arguments,
                "result": {
                    "status": "ok",
                    "cached": True,
                    "stored_at": _cached.get("stored_at"),
                },
                "result_text": str(_cached.get("result_text") or ""),
                "status": "ok",
                "cached": True,
            })
            continue

        # ── Pre-execution commit-gates (veto + decision_gate) ────────
        # Arbitrage udskilt til commit_gate_arbiter (Boy Scout, 2026-07-08). Håndhævelsen er nu
        # GOVERNED pr. gate (gate_enforcement): et RED-verdikt der er kill-switchet fra
        # degraderer til observe-only. Self-safe/fail-open (gate-fejl → allow).
        from core.services.commit_gate_arbiter import evaluate_commit_gates
        _cg = evaluate_commit_gates(
            name=name, arguments=arguments, user_message=user_message,
            session_id=session_id or "", run_id=run_id or "",
        )
        _decision_soft_warn = _cg.soft_warn  # YELLOW: blød grad — tool kører, advarsel surfaces

        if _cg.blocked:
            _gate_reason = _cg.reason or "Ukendt gate-blokering"
            _gate_type = _cg.gate_type or "decision_gate"
            results.append({
                "tool_name": name,
                "arguments": arguments,
                "result": {
                    "status": "gate_blocked",
                    "gate_type": _gate_type,
                    "message": _gate_reason,
                },
                "result_text": f"[{_gate_type}] {_gate_reason}",
                "status": "gate_blocked",
            })
            # Emit telemetry
            try:
                event_bus.publish(f"{_gate_type}.blocked", {
                    "tool_name": name,
                    "reason": _gate_reason[:500],
                    "run_id": run_id,
                })
            except Exception:
                pass
            continue

        result = _exec(name, arguments)
        result_text = format_tool_result_for_model(name, result)
        if _decision_soft_warn:
            # YELLOW (blød decision-tension): tool kørte, men gør Jarvis opmærksom.
            result_text = f"⚠ {_decision_soft_warn}\n\n{result_text}"
        # Only mark as "seen" if the call genuinely succeeded. Including
        # `approval_needed` here was a bug: when approval is later denied
        # OR the approval flow fails silently, the signature stays in the
        # seen-set forever and every retry returns duplicate_suppressed
        # even though the write never happened. Observed today with
        # write_file to /media/projects/mini-jarvis/ — pre-fix that path
        # required approval, approval flow didn't reach the user, signature
        # got stuck, retries blocked. Errors (error/blocked/timeout)
        # likewise MUST stay retryable.
        if controller and result.get("status") == "ok":
            controller.seen_simple_tool_call_signatures.add(signature)
        try:
            from core.services.agentic_tool_cache import store_result
            store_result(
                tool_name=name,
                arguments=arguments,
                result_text=result_text,
                status=str(result.get("status", "ok")),
            )
        except Exception:
            pass
        results.append({
            "tool_name": name,
            "arguments": arguments,
            "result": result,
            "result_text": result_text,
            "status": result.get("status", "ok"),
        })
    return results
