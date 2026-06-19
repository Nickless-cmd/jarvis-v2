"""POST /chat/stream/v2 — Anthropic-style SSE protokol.

Wrapper omkring eksisterende start_visible_run() der oversætter den
gamle protokol til Anthropic-style v2-protokol via translate_to_v2().

Spec: docs/superpowers/specs/2026-06-10-chat-stream-v2-design.md
Translator: core/services/visible_runs_sse_v2.py
Event-dataclasses: apps/api/jarvis_api/sse_v2_events.py

Bemærk: /chat/stream (legacy) eksisterer uændret. v2 er additiv for at
understøtte den nye jarvis-desk app der bygges sideløbende.
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from apps.api.jarvis_api.routes.chat import ChatStreamRequest
from core.runtime.settings import load_settings
from core.services.chat_sessions import append_chat_message, get_chat_session
from core.services.visible_runs import start_visible_run
from core.services.visible_runs_sse_v2 import translate_to_v2

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("/stream/v2")
async def chat_stream_v2(request: ChatStreamRequest) -> StreamingResponse:
    """Anthropic-style streaming alternative til /chat/stream.

    Konsumerer samme request-format, men producerer Anthropic-protokol:
    message_start → content_block_start(text) → content_block_delta(text_delta)*
    → content_block_stop → message_delta → message_stop, med ping
    hver 5 sek og system_event-wrappede Jarvis-specifikke events.
    """
    session_id = request.session_id.strip()
    if not session_id:
        raise HTTPException(
            status_code=400, detail="session_id must be a non-empty string"
        )
    if get_chat_session(session_id) is None:
        raise HTTPException(status_code=404, detail="Chat session not found")

    # Prepend attachment-direktiv-blok (delt helper med v1) så Jarvis ser billeder
    # via analyze_image. Empty-check sker på effective_message → billede-kun virker.
    from apps.api.jarvis_api.routes.attachments import apply_attachment_context
    effective_message = apply_attachment_context(request.message, request.attachment_ids)

    if not (effective_message or "").strip():
        raise HTTPException(
            status_code=400,
            detail="message must not be empty or whitespace-only",
        )

    print(
        f"[chat/stream/v2] session={session_id[:20]} "
        f"message_len={len(effective_message)} "
        f"attachments={list(request.attachment_ids or [])}",
        flush=True,
    )

    from core.identity.workspace_context import current_user_id
    _uid = current_user_id() or None
    append_chat_message(
        session_id=session_id,
        role="user",
        content=effective_message,
        user_id=_uid,
    )

    # Load model/provider/lane settings så vi kan inkludere dem i
    # message_start metadata (klienten skal bruge dem til at display'e
    # "kører på X-model" + til debugging).
    settings = load_settings()

    # Mode → tool-scope. "chat" begrænser værktøjs-listen til samtale-
    # allowlisten (se core.tools.tool_scoping). Andre modes / tom = ubegrænset
    # (rolle-filter gælder stadig).
    _m = (request.mode or "").strip().lower()
    _tool_scope = "chat" if _m == "chat" else "code" if _m == "code" else ""

    # Persistér code-mode workspace-binding på sessionen, så run-enforcement
    # (trusted-folder gate i visible_runs) læser den AKTUELLE workspace — ikke en
    # tom/stale binding fra da sessionen blev oprettet. Også det der tænder
    # code-ikonet i sidebar. Best-effort; må aldrig bryde streamen.
    if _tool_scope == "code":
        _wk = (request.workspace_kind or "").strip()
        _wr = (request.workspace_root or "").strip()
        if _wk and _wr:
            try:
                from core.services.chat_sessions import set_session_workspace
                set_session_workspace(session_id, kind=_wk, root=_wr)
            except Exception:
                pass

    # Rolle-bevidst provider/model-routing (2026-06-13): member→ollama,
    # owner→valg. Helper'en clamper member server-side (kan ikke eskalere).
    from apps.api.jarvis_api.routes.chat import _resolve_visible_target
    _prov_override, _model_override = _resolve_visible_target(
        _uid, request.provider_choice, request.model
    )
    _eff_provider = _prov_override or settings.visible_model_provider
    _eff_model = _model_override or settings.visible_model_name
    # Observability: hvad valgte klienten, og hvad resolver det til? Gør provider-
    # mismatch ("jeg kører ikke ollama") diagnosticerbar uden at gætte.
    print(
        f"[chat/stream/v2] provider_choice={request.provider_choice!r} "
        f"model={request.model!r} → eff_provider={_eff_provider} eff_model={_eff_model}",
        flush=True,
    )
    # Husk den aktive (provider, model) så read_model_config kan vise den faktiske
    # per-run-override — ikke kun global default (ellers modsiger tool'et prompten).
    try:
        from core.services.active_model_state import set_active_visible_target
        set_active_visible_target(_uid, _eff_provider, _eff_model)
    except Exception:
        pass

    if settings.server_authoritative_runs:
        # SERVER-AUTORITATIV: kør detached + abonnér på run-loggen fra offset 0.
        # Runnet lever uafhængigt af denne forbindelse → overlever app-baggrund.
        from core.services.visible_runs_sections.detached_run import (
            start_or_attach_user_run,
        )
        import core.services.run_event_log as rel

        # Single-flight pr. session: hvis et run allerede er LIVE i sessionen,
        # spawn ikke et samtidigt run (det klobber via active-run-singletonen →
        # begge fejler). Helper'en attacher + nudger i stedet. Se helper-docstring.
        run_id, _attached = start_or_attach_user_run(
            message=effective_message,
            session_id=session_id,
            nudge_enabled=bool(getattr(settings, "nudge_system_enabled", True)),
            approval_mode=request.approval_mode,
            thinking_mode=request.thinking_mode,
            force_user_id=_uid,
            tool_scope=_tool_scope,
            provider_override=_prov_override,
            model_override=_model_override,
            eff_model=_eff_model,
            eff_provider=_eff_provider,
            lane=settings.primary_model_lane,
        )
        if _attached:
            print(
                f"[chat/stream/v2] single-flight: session={session_id[:20]} "
                f"attached til live run {run_id[:24]} (ingen nyt run)",
                flush=True,
            )

        async def _subscribe():
            import asyncio as _a
            rel.subscriber_opened(run_id)
            try:
                idx = 0
                empty = 0
                while True:
                    frames, done = rel.read(run_id, idx)
                    for f in frames:
                        idx += 1
                        yield f
                    if done:
                        rel.mark_consumed(run_id)  # saa runnet til ende -> undertryk push
                        break
                    if frames:
                        empty = 0
                    else:
                        empty += 1
                        if empty > 300:  # ~24s helt tavst (pings hver 5s) → giv op
                            break
                    await _a.sleep(0.08)
            finally:
                rel.subscriber_closed(run_id)

        return StreamingResponse(
            _subscribe(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Stream-Protocol": "v2-anthropic",
                "X-Run-Id": run_id,
            },
        )

    # FLAG OFF → nuværende stabile A1-tee (uændret).
    legacy_iter = start_visible_run(
        message=effective_message,
        session_id=session_id,
        approval_mode=request.approval_mode,
        thinking_mode=request.thinking_mode,
        force_user_id=_uid,
        tool_scope=_tool_scope,
        provider_override=_prov_override,
        model_override=_model_override,
    )

    v2_stream = translate_to_v2(
        legacy_iter,
        run_id="",  # plukkes fra første legacy event
        model=_eff_model,
        provider=_eff_provider,
        lane=settings.primary_model_lane,
        session_id=session_id,
        ping_interval_s=5.0,
    )

    # Live session-broadcast (A): tee bruger-runnets v2-frames ind i run_follow-
    # bufferen, så ANDRE klienter på samme session (desk/mobil/webchat) kan
    # følge token-for-token via GET /chat/sessions/{id}/follow — og en mobil der
    # mister sin egen SSE (baggrund/skærm sover) kan re-attache og fange op.
    # Tee'en påvirker ikke den anmodende klients stream; en fejl her må aldrig
    # bryde svaret, så alt run_follow-arbejde er try/except-indkapslet.
    async def _broadcast_tee():
        try:
            from core.services.run_follow import (
                begin_follow,
                end_follow,
                publish_follow_frame,
            )
        except Exception:
            # run_follow utilgængelig → fald tilbage til ren passthrough.
            async for frame in v2_stream:
                yield frame
            return
        try:
            begin_follow(session_id, "")
        except Exception:
            pass
        try:
            async for frame in v2_stream:
                try:
                    publish_follow_frame(session_id, frame)
                except Exception:
                    pass
                yield frame
        finally:
            try:
                end_follow(session_id)
            except Exception:
                pass

    return StreamingResponse(
        _broadcast_tee(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Stream-Protocol": "v2-anthropic",
        },
    )
