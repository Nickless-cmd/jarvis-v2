"""Worker-thread pump for the first visible model stream.

Extracted from visible_runs: scope and run identity must be rebound inside
the worker because async-generator ContextVars do not reliably cross the
yield/thread boundary.
"""
from __future__ import annotations


def pump_first_pass(
    run, *, controller, tool_scope: str, loop, queue, sentinel, stream_fn=None,
) -> None:
    from core.services.run_autonomy_context import (
        set_autonomous, set_run_identity, set_user_present,
    )
    from core.tools.tool_scoping import (
        reset_local_exec,
        reset_tool_scope,
        set_local_exec,
        set_tool_scope,
    )

    set_run_identity(str(run.run_id or ""), str(getattr(run, "origin", "") or ""))
    set_autonomous(bool(getattr(run, "autonomous", False)))
    # Samme tilstedeværelse som hovedkørslen (19/10-2026): uden den ville
    # første-pass-pumpen sammensætte prompten med det autonome katalog, mens
    # resten af turen havde det fulde sæt — to svar på ét spørgsmål.
    try:
        from core.tools.autonomous_tool_policy import presence_for_run
        set_user_present(presence_for_run(run))
    except Exception:
        set_user_present(False)
    scope_token = None
    local_exec_token = None
    try:
        if tool_scope:
            scope_token = set_tool_scope(tool_scope)
        local_exec_token = set_local_exec(bool(getattr(run, "local_tool_exec", False)))
    except Exception:  # scope propagation is best-effort; the model stream still runs
        pass

    if stream_fn is None:
        from core.services.visible_model import stream_visible_model as stream_fn
    try:
        from core.services.visible_memory_grounding import ground_memory_question
        grounded_message = ground_memory_question(run.user_message)
        for item in stream_fn(
            message=grounded_message,
            provider=run.provider,
            model=run.model,
            session_id=run.session_id,
            controller=controller,
            thinking_mode=run.thinking_mode,
        ):
            loop.call_soon_threadsafe(queue.put_nowait, item)
    except Exception as exc:
        loop.call_soon_threadsafe(queue.put_nowait, exc)
    finally:
        # Executor threads are reused: never let this run's identity or
        # autonomy flag bleed into a later visible prompt assembly.
        set_run_identity("", "")
        set_autonomous(False)
        set_user_present(False)
        if local_exec_token is not None:
            reset_local_exec(local_exec_token)
        if scope_token is not None:
            reset_tool_scope(scope_token)
        loop.call_soon_threadsafe(queue.put_nowait, sentinel)
