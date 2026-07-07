"""Memory/continuity post-processing for visible runs.

Boy Scout-udtrækning (2026-07-07): udskilt fra ``core/services/visible_runs.py``
(8593 linjer god-fil). Ren KODE-FLYTNING — ingen logik-ændring. Funktionerne er
leaf-orkestratorer kaldt fra ``_stream_visible_run`` og re-eksporteres tilbage til
``visible_runs`` i bunden af den fil, så bare kald + test-monkeypatches fortsat virker.

Symboler der monkeypatches på ``visible_runs`` (fx ``start_autonomous_run``) refereres
via ``_vr.X`` (facade-seam) så patchen ses på kald-tidspunkt. Main-symboler bruges
KUN inde i funktions-kroppe (lazy), aldrig på modul-niveau → ingen import-cyklus.
"""

from __future__ import annotations

import core.services.visible_runs as _vr

from core.eventbus.bus import event_bus
from core.services.chat_sessions import recent_chat_tool_messages


_CONTINUATION_DELAY_SECONDS = 5.0


def _recent_internal_tool_context(session_id: str | None, *, limit: int = 6) -> str:
    if not session_id:
        return ""
    try:
        messages = recent_chat_tool_messages(session_id, limit=limit)
    except Exception:
        return ""
    lines: list[str] = []
    for item in messages[-limit:]:
        content = " ".join(str(item.get("content") or "").split()).strip()
        if not content:
            continue
        if len(content) > 300:
            content = content[:299].rstrip() + "…"
        lines.append(f"- {content}")
    if not lines:
        return ""
    return "\n".join(
        [
            "Recent internal tool results from this chat.",
            "These are Jarvis-only observations and are not visible user chat:",
            *lines,
        ]
    )


def _run_memory_postprocess(run: "_vr.VisibleRun", assistant_text: str) -> None:
    if not run.session_id:
        return
    distillation_result: dict[str, object] | None = None
    consolidation_result: dict[str, object] | None = None
    errors: list[str] = []

    try:
        from core.services.session_distillation import (
            distill_session_carry,
        )

        distillation_result = distill_session_carry(
            session_id=run.session_id,
            run_id=run.run_id,
        )
    except Exception as exc:
        errors.append(f"session_distillation:{type(exc).__name__}:{exc}")
        event_bus.publish(
            "memory.session_distillation_failed",
            {
                "session_id": run.session_id,
                "run_id": run.run_id,
                "error": str(exc) or type(exc).__name__,
            },
        )

    try:
        from core.services.end_of_run_memory_consolidation import (
            consolidate_run_memory,
        )

        consolidation_result = consolidate_run_memory(
            session_id=run.session_id,
            run_id=run.run_id,
            user_message=run.user_message,
            assistant_response=assistant_text,
            internal_context=_vr._recent_internal_tool_context(run.session_id),
        )
    except Exception as exc:
        errors.append(f"end_of_run_consolidation:{type(exc).__name__}:{exc}")
        event_bus.publish(
            "memory.end_of_run_consolidation_failed",
            {
                "session_id": run.session_id,
                "run_id": run.run_id,
                "error": str(exc) or type(exc).__name__,
            },
        )

    # Generate session summary for cross-session continuity
    session_summary_text = ""
    try:
        from core.services.session_distillation import (
            generate_session_summary,
        )

        session_summary_text = generate_session_summary(
            session_id=run.session_id,
            run_id=run.run_id,
            user_message=run.user_message,
            assistant_response=assistant_text,
        ) or ""
    except Exception as exc:
        errors.append(f"session_summary:{type(exc).__name__}:{exc}")

    # Cross-session threads: create or resume a thread for this session once
    # it has a meaningful title (not "New chat") and a summary. Uses session_id
    # as the de-dup key so we never open more than one thread per session.
    try:
        if session_summary_text:
            from core.services.chat_sessions import get_chat_session
            from core.services.cross_session_threads import (
                create_thread,
                list_threads,
                update_synopsis,
            )
            session_data = get_chat_session(run.session_id) or {}
            title = str(session_data.get("title") or "").strip()
            if title and title.lower() != "new chat":
                existing = [
                    t for t in list_threads()
                    if t.get("opened_in_session") == run.session_id
                ]
                if existing:
                    update_synopsis(existing[0]["thread_id"], session_summary_text[:500])
                else:
                    create_thread(
                        topic=title,
                        synopsis=session_summary_text[:500],
                        status="active",
                        opened_in_session=run.session_id,
                    )
    except Exception as exc:
        errors.append(f"cross_session_threads:{type(exc).__name__}:{exc}")

    # Continuity state capsule: persist after every turn
    try:
        from core.services.continuity import live_update_after_turn

        # Gather mood from mood_oscillator via continuity sync
        mood = {}
        try:
            from core.services.continuity import sync_capsule_mood
            synced = sync_capsule_mood()
            if synced:
                mood = synced
        except Exception:
            pass

        # Gather attention from active goals
        attention = {}
        try:
            from core.services.goal_signal_tracking import list_runtime_goal_signals
            signals = list_runtime_goal_signals(limit=3)
            if signals:
                top = signals[0]
                attention["active_goal_title"] = str(top.get("goal_title", top.get("title", "")))[:80]
                attention["current_focus"] = str(top.get("title", top.get("goal_title", "")))[:80]
        except Exception:
            pass

        # Gather recent activity
        recent_activity = {"last_tool_result_summary": assistant_text[:120]}
        try:
            from core.services.chat_sessions import recent_chat_tool_messages
            tool_msgs = recent_chat_tool_messages(run.session_id, limit=3)
            if tool_msgs:
                tools_used = []
                for tm in tool_msgs:
                    content = str(tm.get("content", "") or "")
                    name = str(tm.get("tool_name", "") or "")
                    if name:
                        tools_used.append(name)
                    elif "tool_use" in str(tm.get("role", "")):
                        tools_used.append(content.split("(")[0][:40])
                recent_activity["tools_used_recently"] = tools_used[:10]
        except Exception:
            pass

        live_update_after_turn(
            mood=mood or None,
            attention=attention or None,
            recent_activity=recent_activity or None,
            session_id=run.session_id,
        )
    except Exception:
        pass

    event_bus.publish(
        "memory.visible_run_postprocess_completed",
        {
            "session_id": run.session_id,
            "run_id": run.run_id,
            "distillation_ran": distillation_result is not None,
            "consolidation_ran": consolidation_result is not None,
            "errors": errors,
            "private_brain_count": (
                distillation_result or {}
            ).get("private_brain_count"),
            "workspace_memory_count": (
                distillation_result or {}
            ).get("workspace_memory_count"),
            "candidate_count": (
                consolidation_result or {}
            ).get("candidate_count"),
            "memory_updated": (
                consolidation_result or {}
            ).get("memory_updated"),
            "user_updated": (
                consolidation_result or {}
            ).get("user_updated"),
            "skipped_reason": (
                consolidation_result or {}
            ).get("skipped_reason"),
        },
    )


def _maybe_trigger_continuation(run: "_vr.VisibleRun", assistant_text: str) -> None:
    """If Jarvis stopped mid-task, trigger an autonomous-run
    that wakes him again with context.

    Guards:
    - Only for visible (non-autonomous) runs — prevents infinite continuation-loop
    - Only if session_id exists (we have somewhere to continue in)
    - Cooldown 45s per session (prevents spam)
    - Only on match with unfinished_intent.detect_unfinished_intent
    - Delay 5s before spawn so user can react first if they see the problem
    - Re-check at spawn: if new visible-run is active in session, abort
    """
    if run.autonomous:
        return  # autonomous runs spawner ikke continuations (loop-beskyttelse)
    if not run.session_id:
        return
    try:
        from core.services.unfinished_intent import (
            detect_unfinished_intent,
            is_in_cooldown,
            mark_triggered,
        )

        # Cooldown check BEFORE detection — saves work
        if is_in_cooldown(run.session_id):
            return

        intent = detect_unfinished_intent(assistant_text)
        if intent is None:
            return

        # Mark cooldown now so concurrent _post_process workers don't both fire
        mark_triggered(run.session_id)

        # Bjørn-gate (16. jun 2026): registrér fremtids-løfter ("jeg gør det /
        # jeg går i gang") så de rejses prominent i NÆSTE turs prompt og holder
        # Jarvis ansvarlig. Fail-soft.
        if intent.pattern == "future_action_promise":
            try:
                from core.services.promise_ledger import record_promise
                record_promise(run.session_id, intent.matched_text)
            except Exception:
                pass

        # Publish for observability — Bjørn can see in Mission Control
        # how often detector fires
        try:
            event_bus.publish(
                "runtime.continuation_triggered",
                {
                    "run_id": run.run_id,
                    "session_id": run.session_id,
                    "pattern": intent.pattern,
                    "matched": intent.matched_text[:100],
                },
            )
        except Exception:
            pass

        # Snippet fra sidste paragraf (mere fokuseret end de sidste N tegn)
        text = assistant_text.strip()
        last_para = text.split("\n\n")[-1] if "\n\n" in text else text
        snippet = (last_para or text)[-400:].strip()

        continuation_message = (
            f"[auto-continuation after pause-pattern '{intent.pattern}'] "
            "You just wrote to the user:\n\n"
            f"---\n{snippet}\n---\n\n"
            "You stopped here — but the task isn't done. The user "
            "already green-lit it. Continue without waiting for a reply. "
            "If you're done, confirm it briefly."
        )

        # Delay spawn so user can react first if they see the problem before we do
        import threading as _threading
        def _delayed_spawn() -> None:
            try:
                import time as _time
                _time.sleep(_CONTINUATION_DELAY_SECONDS)
                # Re-check: if user sent a message in the meantime, then
                # abort — they took over.
                from core.services.visible_runs import _get_active_visible_run_state
                active = _get_active_visible_run_state()
                if active and active.get("session_id") == run.session_id:
                    # A new run is already active in this session — skip continuation
                    return
                _vr.start_autonomous_run(continuation_message, session_id=run.session_id)
            except Exception:
                pass

        _threading.Thread(
            target=_delayed_spawn,
            name=f"continuation-{run.run_id[:12]}",
            daemon=True,
        ).start()
    except Exception:
        pass
