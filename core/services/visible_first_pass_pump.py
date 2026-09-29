"""Worker-thread pump for the first visible model stream.

Extracted from visible_runs: scope and run identity must be rebound inside
the worker because async-generator ContextVars do not reliably cross the
yield/thread boundary.
"""
from __future__ import annotations


def pump_first_pass(
    run, *, controller, tool_scope: str, loop, queue, sentinel, stream_fn=None,
) -> None:
    from core.services.run_autonomy_context import set_autonomous, set_run_identity
    from core.tools.tool_scoping import set_local_exec, set_tool_scope

    set_run_identity(str(run.run_id or ""), str(getattr(run, "origin", "") or ""))
    set_autonomous(bool(getattr(run, "autonomous", False)))
    try:
        if tool_scope:
            set_tool_scope(tool_scope)
        set_local_exec(bool(getattr(run, "local_tool_exec", False)))
    except Exception:  # scope propagation is best-effort; the model stream still runs
        pass

    if stream_fn is None:
        from core.services.visible_model import stream_visible_model as stream_fn
    try:
        for item in stream_fn(
            message=run.user_message,
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
        loop.call_soon_threadsafe(queue.put_nowait, sentinel)
