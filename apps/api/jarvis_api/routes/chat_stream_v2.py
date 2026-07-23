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
from pydantic import BaseModel

from apps.api.jarvis_api.routes.chat import ChatStreamRequest
from core.runtime.settings import load_settings
from core.services.chat_sessions import append_chat_message, get_chat_session
from core.services.visible_runs import start_visible_run
from core.services.visible_runs_sse_v2 import translate_to_v2

router = APIRouter(prefix="/chat", tags=["chat"])


# ── Ollama model-name resolution (2026-07-23) ────────────────────────────────
# Clients (esp. the jarvis-code selector) may send a bare cloud-model name
# ("glm-5.2") while ollama registers it with a tag ("glm-5.2:cloud"). A bare name
# ollama doesn't know → "model not found" → no response. Resolve to the real tag.
import time as _t_ollama
_OLLAMA_TAGS_CACHE: dict = {"ts": 0.0, "tags": set()}
_OLLAMA_TAGS_TTL_S = 120.0


def _ollama_model_tags() -> set:
    """Set of model names ollama currently serves. Cached 120s; fail-open (empty set)."""
    now = _t_ollama.monotonic()
    cached = _OLLAMA_TAGS_CACHE.get("tags") or set()
    if cached and (now - float(_OLLAMA_TAGS_CACHE.get("ts") or 0)) < _OLLAMA_TAGS_TTL_S:
        return cached
    tags: set = set()
    try:
        import json as _json
        import urllib.request as _u
        base = "http://127.0.0.1:11434"
        try:
            _b = str(getattr(load_settings(), "embed_ollama_base_url", "") or "").strip()
            if _b:
                base = _b.rstrip("/")
        except Exception:
            pass
        with _u.urlopen(base + "/api/tags", timeout=3) as _r:
            data = _json.loads(_r.read())
        tags = {str(m.get("name") or "").strip() for m in (data.get("models") or []) if m.get("name")}
    except Exception:
        pass
    if tags:
        _OLLAMA_TAGS_CACHE.update(ts=now, tags=tags)
    return _OLLAMA_TAGS_CACHE.get("tags") or set()


def _resolve_ollama_model_name(model: str) -> str:
    """Resolve a (possibly bare) ollama model name to an actually-served tag.
    'glm-5.2' → 'glm-5.2:cloud' when that variant exists. Fail-open: returns the
    input unchanged if ollama is unreachable or no better match is found."""
    m = (model or "").strip()
    if not m:
        return m
    tags = _ollama_model_tags()
    if not tags or m in tags:
        return m
    for _cand in (f"{m}:cloud", f"{m}:latest"):
        if _cand in tags:
            return _cand
    return m


# ── Path B: local-tool-result submission ─────────────────────────────────────
# The server owns the code-lane transcript and pauses the run at a tool_call; the
# local jarvis-code client executes it and POSTs the result here, correlated by
# call_id. Resolves the waiting run via local_tool_broker. See that module + Path B.
class _ToolResultItem(BaseModel):
    call_id: str
    content: str = ""
    is_error: bool = False


class _ToolResultsBody(BaseModel):
    session_id: str
    results: list[_ToolResultItem]


@router.post("/tool_results")
async def chat_tool_results(body: _ToolResultsBody) -> dict:
    """Client submits locally-executed tool results; resolve the paused visible run."""
    from core.services import local_tool_broker
    resolved = 0
    for item in body.results:
        if local_tool_broker.resolve(item.call_id, item.content, is_error=item.is_error):
            resolved += 1
    return {"resolved": resolved, "total": len(body.results), "session_id": body.session_id}


# ── Prewarm-on-return: session-bevidst DeepSeek prefix-cache-varme ────────────
# ROD (målt 2026-07-21): DeepSeeks prefix-cache af en sessions [system][historik]
# udløber i pauser (~30-120 min) → første besked efter en pause prefiller hele
# ~32k-prompten fra bunden (16-48% hit vs 86-88% varm) = de oplevede >10s. Både
# desk (composer-fokus) og jarvis-code (input-fokus) kalder dette endpoint når
# brugeren vender tilbage, så cachen er varm inden han trykker send. Fire-and-
# forget: returnerer straks, warm kører i baggrundstråd. Se session_prewarm.
class _WarmBody(BaseModel):
    session_id: str
    provider_choice: str = "deepseek"
    model: str = "deepseek-v4-flash"
    mode: str = ""


@router.post("/warm")
async def chat_warm(body: _WarmBody) -> dict:
    """Varm den aktive sessions prefix i DeepSeeks cache (prewarm-on-return).

    Auth-gatet som resten af /chat. Fanger den autentificerede kontekst NU (den
    tabes i baggrundstråden) og fyrer warm_session_prefix_async. Returnerer straks
    så klienten aldrig blokeres. Kun deepseek + eksisterende session varmes; alt
    andet no-op'er lydløst (medlemmer på ollama har ingen prefix-cache at varme)."""
    from core.identity.workspace_context import (
        current_user_id, current_role, effective_role, current_workspace_name,
    )
    sid = str(body.session_id or "").strip()
    if not sid:
        return {"status": "skipped", "reason": "no-session"}
    if get_chat_session(sid) is None:
        return {"status": "skipped", "reason": "unknown-session"}
    try:
        _role = effective_role() or current_role() or "owner"
    except Exception:
        _role = "owner"
    from core.services.session_prewarm import warm_session_prefix_async
    warm_session_prefix_async(
        sid,
        provider=str(body.provider_choice or "deepseek"),
        model=str(body.model or "deepseek-v4-flash"),
        user_id=current_user_id() or "",
        role=_role,
        workspace_name=current_workspace_name() or "bjorn",
    )
    return {"status": "warming", "session_id": sid}


def maybe_handle_override(text: str, session_id: str) -> dict | None:
    """Owner-override (§6.3) i webchat/desk-kanalen: `!override <TOTP>` /
    `!revoke-override`. Wiret her ligesom discord/telegram-gatewayen — ellers
    aktiverer Bjørns override ALDRIG remote, og operator-tools i en member-session
    (fx hans mors Mac) forbliver tool_not_permitted (root cause, Bjørn 2026-06-21).

    Thin wire; ren TOTP-logik i override_command. Returnerer handler-dict'et (med
    `reply`) hvis teksten ER en override-kommando, ellers None (normal tur kører).
    Best-effort: en fejl må aldrig spærre normal chat → returnér None ved exception.
    """
    try:
        from core.services.override_command import handle_override_command
        from core.identity.users import get_owner, get_totp_seed
        _owner = get_owner()
        _seed = get_totp_seed(discord_id=_owner.discord_id) if _owner else ""
        return handle_override_command(text or "", session_id=session_id, owner_seed=_seed)
    except Exception:
        return None


def _override_v2_response(
    reply: str, *, session_id: str, model: str, provider: str, lane: str
) -> StreamingResponse:
    """Byg et minimalt men protokol-korrekt v2-SSE-svar for en override-kvittering,
    så turen kortsluttes uden et LLM-run (klienten forlader kun 'working' på
    message_stop — derfor SKAL hele sekvensen emitteres)."""
    from apps.api.jarvis_api.sse_v2_events import (
        MessageStart, ContentBlockStart, ContentBlockDelta,
        ContentBlockStop, MessageDelta, MessageStop,
    )

    async def _gen():
        yield MessageStart(run_id="override", model=model, provider=provider,
                           lane=lane, session_id=session_id).to_sse_line()
        yield ContentBlockStart(index=0, block_type="text").to_sse_line()
        yield ContentBlockDelta(index=0, delta_type="text_delta", content=reply).to_sse_line()
        yield ContentBlockStop(index=0).to_sse_line()
        yield MessageDelta(stop_reason="end_turn").to_sse_line()
        yield MessageStop().to_sse_line()

    return StreamingResponse(
        _gen(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Stream-Protocol": "v2-anthropic",
            "X-Run-Id": "override",
        },
    )


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
    # END-TO-END TURN TRACE (gated: touch /tmp/jarvis-turn-trace). Marks the moment
    # jarvis-desk's send is registered by the visible lane — the true start of the
    # route. Full timeline (request_in → assembly → prompt_leaves → deepseek
    # first_token/done → response_landed) dumps to /tmp/jarvis-turn-trace-dumps.
    try:
        from core.services import turn_trace as _tt_route
        _tt_route.start(f"desk send session={session_id[:12]} len={len(effective_message)}")
        _tt_route.mark("request_in", "chat_stream_v2 (desk send registered)")
    except Exception:
        pass
    append_chat_message(
        session_id=session_id,
        role="user",
        content=effective_message,
        user_id=_uid,
    )

    # Paste-store (spec 2026-07-09): den PERSISTEREDE besked beholder den kompakte
    # `[paste:<id> +N linjer]`-reference (kompakt historik), men modellen ser som
    # default den FULDE paste-tekst. Ekspandér referencer FØR runnet. Flag
    # `paste_inline_to_model` (default ON) styrer det; ukendt id → behold referencen
    # (degradér, crash aldrig). Ingen reference → identitet (no-op).
    try:
        from core.services.paste_store import project_paste_for_model
        model_message = project_paste_for_model(effective_message)
    except Exception:
        model_message = effective_message

    # Load model/provider/lane settings så vi kan inkludere dem i
    # message_start metadata (klienten skal bruge dem til at display'e
    # "kører på X-model" + til debugging).
    settings = load_settings()

    # Owner-override (§6.3) — TOTP-verificeret elevering fra denne (evt. member-)
    # session. SKAL ligge FØR run-start: en `!override <kode>` kortsluttes med en
    # kvittering og kører ALDRIG et LLM-run. Dette er Bjørns remote kill-switch/
    # kontrol — uden denne wiring aktiverede den aldrig i app-kanalen.
    _ov = maybe_handle_override(request.message, session_id)
    if _ov is not None:
        _reply = str(_ov.get("reply") or "")
        try:
            append_chat_message(session_id=session_id, role="assistant",
                                content=_reply, user_id=None)
        except Exception:
            pass
        print(f"[chat/stream/v2] override-kommando: session={session_id[:20]} "
              f"ok={_ov.get('ok')} action={_ov.get('action') or _ov.get('reason')}", flush=True)
        return _override_v2_response(
            _reply, session_id=session_id,
            model=settings.visible_model_name,
            provider=settings.visible_model_provider,
            lane=settings.primary_model_lane,
        )

    # Normal besked i en ELEVET session → forny override-vinduet (5 min rullende).
    # KRITISK (Bjørn 2026-06-21): uden dette udløber 90s-startvinduet midt i en
    # operator-sekvens og operator-tools/sudo låses igen ("virker én gang, så blok").
    # effective_role()'s egen touch() kører i den lossy executor-kontekst (session_id/
    # rolle-flip) og fornyer ikke pålideligt — her har vi det korrekte session_id.
    try:
        from core.services import override_store as _ovs
        if _ovs.is_active(session_id):
            _ovs.touch(session_id)
    except Exception:
        pass

    # Identity-guard & session-lock (spec 2026-06-21): kør FØR LLM. Låst session/
    # konto eller et uverificeret identitets-claim ("jeg hedder Bjørn" i en andens
    # session) → kortslut med kvittering, intet LLM-run. Override-blokken ovenfor
    # kører FØRST, så owner altid kan komme til (og låse op igen).
    try:
        from core.services import identity_guard as _ig
        _guard = _ig.guard_incoming(request.message, session_id=session_id, user_id=_uid or "")
    except Exception:
        _guard = None
    if _guard is not None:
        _greply = str(_guard.get("reply") or "")
        try:
            append_chat_message(session_id=session_id, role="assistant",
                                content=_greply, user_id=None)
        except Exception:
            pass
        print(f"[chat/stream/v2] identity-guard: session={session_id[:20]} "
              f"action={_guard.get('action')}", flush=True)
        return _override_v2_response(
            _greply, session_id=session_id,
            model=settings.visible_model_name,
            provider=settings.visible_model_provider,
            lane=settings.primary_model_lane,
        )

    # Mode → tool-scope. "chat" begrænser værktøjs-listen til samtale-
    # allowlisten (se core.tools.tool_scoping). Andre modes / tom = ubegrænset
    # (rolle-filter gælder stadig).
    _m = (request.mode or "").strip().lower()
    _tool_scope = "chat" if _m == "chat" else "code" if _m == "code" else ""
    # Path B (server-owned transcript, LOCAL tool execution): only honoured in code
    # scope — the jarvis-code client is the one that runs the tools locally. Default
    # OFF everywhere → existing clients are byte-identical.
    _local_exec = bool(getattr(request, "local_tool_exec", False)) and _tool_scope == "code"

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
    # Ollama model-name normalization (2026-07-23): the jarvis-code selector sends
    # bare cloud names ("glm-5.2") but ollama registers cloud models with a ":cloud"
    # tag ("glm-5.2:cloud"). A bare name → ollama "model 'glm-5.2' not found" → the
    # code lane returns NO response. Resolve the bare name to the actual ollama tag
    # (adds ":cloud"/":latest" when that variant exists). Cached; fail-open (unchanged
    # if ollama can't be reached). Only touches the ollama provider.
    if _eff_provider == "ollama":
        _eff_model = _resolve_ollama_model_name(_eff_model)
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
            message=model_message,
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
            local_tool_exec=_local_exec,
        )
        if _attached:
            print(
                f"[chat/stream/v2] single-flight: session={session_id[:20]} "
                f"attached til live run {run_id[:24]} (ingen nyt run)",
                flush=True,
            )

        async def _subscribe():
            import asyncio as _a
            import time as _xt
            from apps.api.jarvis_api.sse_v2_events import Ping as _Ping
            rel.subscriber_opened(run_id)
            saw_stop = False
            # Klient-keepalive: emit vores EGEN ping hvert _PING_GAP_S når der ikke
            # flyder relay-frames. Det detached runs ping-loop kører på et separat
            # (evt. blokeret) event-loop OG dets pings droppes fra relay-bufferen
            # (ephemeral) → de når ALDRIG klienten. Denne ping kører på den sunde
            # API-loop og er den eneste klienten ser i et content-gap → desk's 90s
            # ping-watchdog fyrer ikke mens et langt run/tool-runde er stille.
            _PING_GAP_S = 5.0
            _last_emit = _xt.monotonic()
            try:
                idx = 0
                empty = 0
                while True:
                    frames, done = rel.read(run_id, idx)
                    for f in frames:
                        idx += 1
                        if "message_stop" in f:
                            saw_stop = True
                        yield f
                        _last_emit = _xt.monotonic()
                    if saw_stop:
                        # POST-SVAR-HÆNG-FIX (2026-07-18): message_stop ER klientens
                        # terminal. Luk streamen NU i stedet for at vente på mark_done —
                        # run-generatoren kører memory-absorb/cognitive post-processing
                        # EFTER message_stop men før mark_done, så at vente lod streamen
                        # hænge X sek efter teksten var landet. Post-processing fortsætter
                        # i baggrunden (detached run); klienten er færdig ved terminal.
                        # mark_consumed → andre overflader re-pusher ikke.
                        rel.mark_consumed(run_id)
                        break
                    if done:
                        # TERMINAL-GARANTI (Bjørn 29. jun, stream_stall-roden): runnet er
                        # 'done', men hvis INGEN message_stop-frame nåede relayet (glm-5.2
                        # stall/abnorm/tom completion → central-nerve stream_stall) ville vi
                        # bare bryde → klienten får ALDRIG en terminal → hænger på 'working'
                        # → onHung (90s) → reattach (timer NULSTILLER til 0) → "anden enhed
                        # følger med"-banner → resten kører som follow på mobil. Vi syntetiserer
                        # message_stop så desk's egen stream ALTID ender rent (status=done).
                        if not saw_stop:
                            yield rel.synthetic_terminal_frame(
                                run_id, session_id, reason="run_done_no_stop"
                            )
                        rel.mark_consumed(run_id)  # saa runnet til ende -> undertryk push
                        break
                    if frames:
                        # Frames FLYDER → poll hurtigt (15ms) så tokens/tool-frames når
                        # klienten ét-for-ét i stedet for 80ms-klumper. Fluid streaming.
                        # Kun aktiv mens der reelt strømmer content (få sekunder pr. tur),
                        # så CPU-omkostningen er forsvindende. Idle-stien bevarer 80ms.
                        empty = 0
                        await _a.sleep(0.015)
                        continue
                    empty += 1
                    # Klient-keepalive ping i content-gap (se _PING_GAP_S ovenfor).
                    if (_xt.monotonic() - _last_emit) >= _PING_GAP_S:
                        yield _Ping().to_sse_line()
                        _last_emit = _xt.monotonic()
                    if empty > 300 and rel.is_live(run_id):
                        # ROD (Bjørn 29. jun, instrumenterings-bevist): glm-5.2's tænke/assembly-
                        # fase producerer ~ingen relay-frames i ~24s (ping-starvation) →
                        # give-up'en fyrede MENS runnet stadig var LIVE → syntetisk
                        # message_stop → desk's stream døde ved 24s → /live (mobil)
                        # overtog → ALT content (kom efter 24s) gik til mobil. Giv KUN op
                        # hvis runnet er ÆGTE dødt (ikke is_live); ellers bliv ved at vente.
                        empty = 0
                    elif empty > 300:  # ~24s tavst OG run ikke længere live → giv op
                        # H1/G6: aldrig bare break — emit syntetisk terminal-frame
                        # så klienten forlader 'working', + fyr subscriber_timeout-nerve.
                        yield rel.synthetic_terminal_frame(
                            run_id, session_id, reason="relay_subscriber_idle"
                        )
                        break
                    # Idle → langsom poll: sparer CPU + holder ping/timeout-kadencen
                    # (empty>300 ≈ 24s uændret, da kun tomme polls tæller ved 80ms).
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
        message=model_message,
        session_id=session_id,
        approval_mode=request.approval_mode,
        thinking_mode=request.thinking_mode,
        force_user_id=_uid,
        tool_scope=_tool_scope,
        provider_override=_prov_override,
        model_override=_model_override,
        local_tool_exec=_local_exec,
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
        _tt_first = True
        try:
            async for frame in v2_stream:
                if _tt_first:
                    try:
                        from core.services import turn_trace as _tt_r
                        _tt_r.mark("first_frame", "first v2 frame → client")
                    except Exception:
                        pass
                    _tt_first = False
                try:
                    publish_follow_frame(session_id, frame)
                except Exception:
                    pass
                yield frame
        finally:
            try:
                from core.services import turn_trace as _tt_r2
                _tt_r2.mark("response_landed", "stream complete → client")
                _tt_r2.dump("desk turn complete")
            except Exception:
                pass
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
