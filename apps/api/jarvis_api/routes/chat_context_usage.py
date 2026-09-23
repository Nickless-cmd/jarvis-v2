"""Kontekstforbrug og komprimeringsstatus til Desk.

Udskilt fra chat.py, så måling og visning har ét afgrænset ansvar.
"""
from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()


def _compactions_for_session(session_id: str) -> list[dict]:
    """Successful marker savings from the compaction log, never summary text."""
    if not session_id:
        return []
    try:
        from core.runtime.db import connect
        with connect() as conn:
            rows = conn.execute(
                "SELECT marker_id, tokens_foer, tokens_efter FROM compaction_log "
                "WHERE session_id = ? AND fremdrift = 1 AND marker_id != '' "
                "ORDER BY id DESC LIMIT 100", (session_id,),
            ).fetchall()
        return [
            {
                "marker_id": str(row[0]),
                "tokens_before": int(row[1]),
                "tokens_after": int(row[2]),
                "freed_tokens": max(0, int(row[1]) - int(row[2])),
            }
            for row in rows
        ]
    except Exception:
        # The log may not exist yet in a newly initialized runtime.
        return []

@router.get("/context-info")
def chat_context_info() -> dict:
    """Kontekst-tærskler til composer-ringen (#9). Kun ægte config-tal:
    autocompact-punktet (context_compact_threshold_tokens). Klienten holder
    selv tælleren (usage.input + cache fra streamen)."""
    from core.runtime.settings import load_settings
    s = load_settings()
    # 2026-07-18: ringen måler nu mod ATTENTION-budgettet (den PRIMÆRE trigger), så den
    # rammer ~100% netop når compaction fyrer — ikke mod de gamle 130k som aldrig blev nået.
    return {
        "compact_at": int(getattr(s, "context_attention_budget_tokens", 35_000) or 35_000),
        "run_compact_at": int(s.context_run_compact_threshold_tokens or 0),
    }


@router.get("/context-usage")
async def chat_context_usage(
    session_id: str = "", provider: str = "", model: str = "",
) -> dict:
    """ÆGTE kontekst-fyld for en session — backend-autoritativt.

    Returnerer `tokens` = estimat af det FAKTISKE transcript der sendes til modellen siden
    sidste compact (præcis det tal autocompact selv måler mod context_compact_threshold_tokens).
    DERFOR harmonerer ringen med autocompact: den vokser mod loftet og FALDER når compaction
    fyrer — i stedet for den gamle per-tur stream-usage der nulstilledes hver besked.

    Plus `compacting` (baggrunds-compaction kører lige nu) + `compacted` (en summary findes)
    til liveness/compaction-indikatoren over composeren.
    """
    import asyncio

    from core.runtime.settings import load_settings
    s = load_settings()
    # Ringen måler mod attention-budgettet (primær trigger, 2026-07-18) → falder når
    # baggrunds-compaction fyrer ved 35k, i stedet for at snige mod de gamle 130k.
    compact_at = int(getattr(s, "context_attention_budget_tokens", 35_000) or 35_000)

    # System-overhead (stabil prefix: SOUL/IDENTITY/USER/regler/tools) — det FASTE der
    # sendes til modellen udover samtalen. Til tooltip'ens ÆGTE total-tal. Memoiseret
    # (skifter kun ved workspace-edit), self-safe → 0.
    overhead_tokens = await asyncio.to_thread(_system_overhead_tokens, provider, model, session_id)

    tokens = 0
    compacted = False
    if session_id:
        try:
            from core.context.token_estimate import estimate_messages_tokens
            from core.services.prompt_contract import _build_structured_transcript_messages
            msgs = await asyncio.to_thread(
                _build_structured_transcript_messages, session_id, limit=60, include=True,
                # Kun maal. Denne poll startede komprimeringer midt i hans ture
                # og kunne omskrive markoeren med et LLM-kald (16/9-2026).
                bivirkninger=False,
            )
            tokens = int(estimate_messages_tokens(msgs))
        except Exception:
            tokens = 0
        try:
            from core.services.chat_sessions import get_compact_marker
            compacted = bool(await asyncio.to_thread(get_compact_marker, session_id))
        except Exception:
            compacted = False

    # Model-BEVIDST: det AKTIVE models reelle vindue (glm-5.1 256k / glm-5.2·flash 1M).
    model_window = 0
    if provider or model:
        try:
            from core.services.model_context import model_context_window
            model_window = int(model_context_window(provider, model) or 0)
        except Exception:
            model_window = 0
    effective = min(model_window, compact_at) if model_window > 0 else compact_at

    compacting = False
    try:
        from core.services import prompt_contract as _pc
        compacting = bool(session_id) and session_id in getattr(_pc, "_compact_inflight", set())
    except Exception:
        compacting = False
    # Det lokale set ser kun DENNE proces. Komprimeringen kan vaere startet i den
    # anden — se compaction_signal. `last_compact_at` lader klienten hente
    # beskederne igen naar en ny markoer er landet.
    last_compact_at = ""
    if session_id:
        from core.context import compaction_signal as _cs
        compacting = compacting or await asyncio.to_thread(_cs.er_i_gang, session_id)
        last_compact_at = await asyncio.to_thread(_cs.seneste_komprimering, session_id)

    return {
        "tokens": tokens,
        "compact_at": compact_at,
        "effective": effective,
        "model_window": model_window,
        "overhead_tokens": overhead_tokens,
        "compacting": compacting,
        "last_compact_at": last_compact_at,
        "compacted": compacted,
        "compactions": await asyncio.to_thread(_compactions_for_session, session_id),
    }


# System-overhead-cache (stabil prefix ændrer sig kun ved workspace-edit → 60s TTL nok).
_overhead_cache: dict[tuple, tuple[float, int]] = {}


def _system_overhead_tokens(provider: str, model: str, session_id: str) -> int:
    """Estimér tokens i den STABILE system-prefix (identitet + regler + tool-katalog) — det
    faste overhead udover samtalen. Memoiseret pr. (provider, model). Self-safe → 0."""
    import time as _t
    key = (str(provider or ""), str(model or ""))
    now = _t.monotonic()
    hit = _overhead_cache.get(key)
    if hit and (now - hit[0]) < 60:
        return hit[1]
    try:
        from core.services.prompt_contract import build_visible_stable_prefix
        from core.context.token_estimate import estimate_tokens
        name = "default"
        try:
            from core.services.chat_sessions import get_session_owner
            from core.identity.users import find_user_by_discord_id
            oid = get_session_owner(session_id) or "" if session_id else ""
            u = find_user_by_discord_id(oid) if oid else None
            if u and getattr(u, "workspace", ""):
                name = u.workspace
        except Exception:  # Workspace-opslag er valgfrit; brug standardnavnet ved fejl.
            pass
        prefix = build_visible_stable_prefix(provider=provider, model=model, name=name)
        val = int(estimate_tokens(prefix))
        _overhead_cache[key] = (now, val)
        return val
    except Exception:  # Ringens ekstra overhead-estimat må ikke blokere statusruten.
        return 0


class _CompactNowBody(BaseModel):
    session_id: str
    focus: str = ""


@router.post("/compact-now")
def chat_compact_now(body: _CompactNowBody) -> dict:
    """Manuel compaction (som Claude Codes /compact). Udløser den SAMME baggrunds-motor som
    auto-triggeren — round-atomisk 2-trins struktureret summary — men NU, uanset om
    attention-budgettet er nået. Valgfri `focus` styrer hvad summary'en prioriterer.
    Sætter `_compact_inflight` så desk-liveness-linjen tænder. Non-blocking: returnerer straks.
    """
    import threading as _t

    session_id = (body.session_id or "").strip()
    focus = (body.focus or "").strip() or None
    if not session_id:
        return {"started": False, "reason": "missing session_id"}

    from core.services import prompt_contract as _pc
    from core.runtime.settings import load_settings
    s = load_settings()
    low_water = int(getattr(s, "context_attention_low_water_tokens", 15_000) or 15_000)
    keep_recent = int(getattr(s, "context_keep_recent", 20) or 20)

    lock = getattr(_pc, "_compact_inflight_lock", None)
    inflight = getattr(_pc, "_compact_inflight", None)
    if lock is None or inflight is None:
        return {"started": False, "reason": "compaction unavailable"}
    with lock:
        if session_id in inflight:
            return {"started": False, "reason": "already compacting"}
        inflight.add(session_id)
    try:
        _t.Thread(
            target=_pc._run_session_compaction,
            args=(session_id, keep_recent),
            kwargs={"low_water_tokens": low_water, "focus": focus},
            name=f"compact-manual-{session_id[:10]}", daemon=True,
        ).start()
    except Exception as exc:
        with lock:
            inflight.discard(session_id)
        return {"started": False, "reason": f"spawn failed: {exc}"}
    return {"started": True, "reason": "manual", "focus": focus or ""}

