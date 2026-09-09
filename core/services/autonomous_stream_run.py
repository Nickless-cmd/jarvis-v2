"""Server-authoritative streaming lifecycle for autonomous visible runs."""
from __future__ import annotations


def start_autonomous_stream_run(
    message: str,
    *,
    session_id: str | None,
    origin: str = "autonomous",
) -> None:
    """Start autonomous work and relay its v2 frames through ``run_event_log``.

    Governance jobs, including wakeup dispatch, run in the API process. Registering
    before the worker starts makes the run immediately visible to ``/active-runs``
    and attachable through ``/sessions/{id}/live``.
    """
    import contextvars
    import threading
    from uuid import uuid4

    import core.services.run_event_log as relay
    import core.services.visible_runs as vr
    from core.services.central_router_adapt import resolve_autonomous_model

    sid = (session_id or "").strip()
    if not sid:
        from core.services.autonomous_sessions import (
            normalize_origin,
            resolve_autonomous_session,
        )

        sid = resolve_autonomous_session(normalize_origin(origin))

    settings = vr.load_settings()
    provider, model = resolve_autonomous_model(
        autonomous_provider=settings.autonomous_model_provider,
        autonomous_model=settings.autonomous_model_name,
    )
    run = vr.VisibleRun(
        run_id=f"autonomous-{uuid4().hex}",
        lane=settings.primary_model_lane,
        provider=provider,
        model=model,
        user_message=(message or "").strip() or "Autonomous heartbeat check-in",
        session_id=sid,
        autonomous=True,
    )

    from core.services.run_follow import begin_follow

    relay.create(run.run_id, sid)
    begin_follow(sid, run.run_id)
    vr.event_bus.publish(
        "runtime.autonomous_run_started",
        {
            "run_id": run.run_id,
            "session_id": sid,
            "provider": run.provider,
            "model": run.model,
            "focus": run.user_message[:200],
            "origin": origin,
            "autonomous": True,
        },
    )
    try:
        from core.services.central_core import central

        central().observe({
            "cluster": "autonomous",
            "nerve": "autonomous_history",
            "kind": "run_started",
            "origin": origin,
            "session_id": sid,
            "run_id": run.run_id,
        })
    except Exception:
        pass

    def _in_thread() -> None:
        import asyncio

        from core.services.run_follow import end_follow, publish_follow_frame
        from core.services.visible_runs_sse_v2 import translate_to_v2

        loop = asyncio.new_event_loop()
        consumed_frames = 0
        failed = False

        async def _consume() -> None:
            nonlocal consumed_frames
            generator = translate_to_v2(
                vr._stream_visible_run(run),
                run_id=run.run_id,
                model=run.model,
                provider=run.provider,
                lane=run.lane,
                session_id=sid,
                ping_interval_s=5.0,
            )
            try:
                async for frame in generator:
                    consumed_frames += 1
                    relay.append(run.run_id, frame)
                    publish_follow_frame(sid, frame)
            finally:
                try:
                    await generator.aclose()
                except Exception:
                    pass

        try:
            loop.run_until_complete(_consume())
        except Exception as exc:
            failed = True
            vr.event_bus.publish(
                "runtime.autonomous_run_failed",
                {
                    "run_id": run.run_id,
                    "session_id": sid,
                    "provider": run.provider,
                    "model": run.model,
                    "focus": run.user_message[:200],
                    "error": str(exc)[:500],
                    "consumed_frames": consumed_frames,
                },
            )
            vr._observe_autonomous_run(
                run=run,
                session_id=sid,
                outcome="failed",
                frames=consumed_frames,
                error=str(exc),
            )
        finally:
            relay.mark_done(run.run_id)
            end_follow(sid)
            try:
                relay.prune()
            except Exception:
                pass
            try:
                state = vr._get_active_visible_run_state() or {}
                if str(state.get("session_id") or "") == sid:
                    vr._set_active_visible_run({})
            except Exception:
                pass
            if not failed:
                outcome = vr.get_last_visible_run_outcome() or {}
                interrupted = (
                    str(outcome.get("run_id") or "") == run.run_id
                    and str(outcome.get("status") or "") == "interrupted"
                )
                status = "interrupted" if interrupted else "completed"
                payload = {
                    "run_id": run.run_id,
                    "session_id": sid,
                    "provider": run.provider,
                    "model": run.model,
                    "focus": run.user_message[:200],
                    "consumed_frames": consumed_frames,
                }
                if interrupted:
                    payload["error"] = str(outcome.get("error") or "")[:500]
                else:
                    payload["autonomous"] = True
                vr.event_bus.publish(f"runtime.autonomous_run_{status}", payload)
                vr._observe_autonomous_run(
                    run=run,
                    session_id=sid,
                    outcome=status,
                    frames=consumed_frames,
                    error=str(outcome.get("error") or "") if interrupted else "",
                )
            loop.close()

    context = contextvars.copy_context()
    threading.Thread(
        target=lambda: context.run(_in_thread),
        name="jarvis-autonomous-stream-run",
        daemon=True,
    ).start()
