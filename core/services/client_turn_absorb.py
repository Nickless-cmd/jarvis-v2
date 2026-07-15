"""client_turn_absorb.py — fyr den fulde post-tur-hjerne for en KLIENT-drevet tur.

Delt substrat (jarvis-code ↔ v2 forening): klienten driver loopet, men serveren ejer
hjernen. Ved tur-slut POSTer klienten turen hertil → vi fyrer SAMME post-process som
`visible_runs._post_process` ville for en server-drevet tur:
  - `set_last_visible_run_outcome` → kaskader til `_update_cognitive_systems_async` (~25 systemer)
  - `_track_runtime_candidates` (~61 trackers: self-model/self-review/world-model/goal/…)
  - `_run_memory_postprocess` (distillation, konsolidering, session-summary, experiential)

Kør i en baggrundstråd i korrekt `user_context` (så memory/workspace scoper til den rette
bruger). Self-safe: hver del wrapped, en fejl bræekker aldrig klientens tur. Uden dette
mister en klient-drevet tur hele hjerne-læringen — derfor er dette Fase B's kerne.
"""
from __future__ import annotations

import logging
import threading
from typing import Any

logger = logging.getLogger(__name__)


def _do_absorb(run: Any, assistant_response: str, user_id: str) -> None:
    """Synkron post-process-firing (testbar). Kører i user_context så memory/workspace
    scoper korrekt. Hver del er wrapped — en fejl stopper ikke de øvrige."""
    from core.identity.workspace_context import user_context
    ctx_kwargs = {"discord_id": str(user_id)} if user_id else {}
    with user_context(**ctx_kwargs):
        from core.services.visible_runs_cognitive import _track_runtime_candidates
        from core.services.visible_runs_memory import _run_memory_postprocess
        from core.services.visible_runs_outcomes import set_last_visible_run_outcome
        steps = (
            ("outcome+cognitive", lambda: set_last_visible_run_outcome(
                run, status="completed", text_preview=assistant_response)),
            ("runtime_candidates", lambda: _track_runtime_candidates(run, assistant_response)),
            ("memory_postprocess", lambda: _run_memory_postprocess(run, assistant_response)),
        )
        for label, fn in steps:
            try:
                fn()
            except Exception:
                logger.debug("client_turn_absorb: %s fejlede", label, exc_info=True)


def persist_client_turn(*, session_id: str, user_message: str, assistant_response: str,
                        user_id: str = "") -> bool:
    """Fase C1 (delte sessioner): persistér en KLIENT-drevet turs beskeder til den DELTE
    server-session, så turen bliver synlig i desk/web/mobil (cross-surface kontinuitet).
    Kun for ægte server-sessioner (`chat-<hex>`) — lokale uuid-sessioner springes over
    (undgår orphan chat_messages-rækker uden en chat_sessions-ejer). Synkron (så turen
    ER persisteret før klienten fortsætter). Self-safe → False ved fejl/ikke-server-session."""
    sid = str(session_id or "")
    if not sid.startswith("chat-"):
        return False
    try:
        from core.services.chat_sessions import append_chat_message
        uid = str(user_id or "") or None
        if user_message:
            append_chat_message(session_id=sid, role="user", content=str(user_message), user_id=uid)
        if assistant_response:
            append_chat_message(session_id=sid, role="assistant",
                                content=str(assistant_response), user_id=uid)
        return True
    except Exception:
        logger.debug("persist_client_turn fejlede", exc_info=True)
        return False


def absorb_client_turn(*, session_id: str, run_id: str, user_message: str,
                       assistant_response: str, provider: str = "", model: str = "",
                       user_id: str = "", lane: str = "agent") -> None:
    """Konstruér en VisibleRun fra klient-data og fyr post-process i en baggrundstråd
    (ikke-blokerende — klientens tur er allerede afsluttet). Self-safe."""
    try:
        from core.services.visible_runs import VisibleRun
        run = VisibleRun(
            run_id=str(run_id or ""), lane=str(lane or "agent"),
            provider=str(provider or ""), model=str(model or ""),
            user_message=str(user_message or ""),
            session_id=(str(session_id or "") or None),
        )
    except Exception:
        logger.debug("client_turn_absorb: kunne ikke konstruere VisibleRun", exc_info=True)
        return
    threading.Thread(
        target=_do_absorb, args=(run, str(assistant_response or ""), str(user_id or "")),
        daemon=True,
    ).start()
