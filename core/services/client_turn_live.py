"""client_turn_live.py — cross-device live-broadcast for en KLIENT-drevet tur (C2b).

Delt substrat (jarvis-code ↔ v2 forening): jarvis-code driver loopet klient-side, så
serveren ser ikke turen som et "kørende run". Uden dette lyser desk/mobils aktivitets-
poller, liveness-linje, header-spinner, systray-ikon og takeover-banner ALDRIG op for
en jarvis-code-tur — Jarvis ville føles "død" på de andre enheder mens han arbejder i
terminalen.

Modulet registrerer turen som det AKTIVE visible run (DB → cross-proces liveness) og
åbner en run_follow-kanal keyed på den delte session, så andre enheder på samme session
kan re-attache. Symmetrisk lifecycle: `begin_live_turn` (liveness ON) → `end_live_turn`
(liveness OFF, kaldes ALTID i klientens finally, også ved fejl/afbrud). Self-safe: hver
del wrapped; en fejl bræekker aldrig klientens tur.
"""
from __future__ import annotations

import logging
from datetime import UTC, datetime

logger = logging.getLogger(__name__)


def begin_live_turn(*, session_id: str, run_id: str, user_message: str = "",
                    provider: str = "", model: str = "", user_id: str = "") -> None:
    """Registrér turen som det aktive visible run + åbn run_follow (kun for ægte
    chat-<hex>-sessioner). Self-safe — hver del wrapped."""
    try:
        from core.services.visible_runs_sections.run_control_state import (
            _set_active_visible_run,
        )
        now = datetime.now(UTC).isoformat()
        _set_active_visible_run({
            "active": True,
            "run_id": str(run_id or ""),
            "lane": "agent",
            "provider": str(provider or ""),
            "model": str(model or ""),
            "session_id": str(session_id or ""),
            "started_at": now,
            "last_activity_at": now,
            "current_user_message_preview": str(user_message or "")[:200],
            "origin": "jarvis-code",
            "user_id": str(user_id or ""),
        })
    except Exception:
        logger.debug("begin_live_turn: active-run set fejlede", exc_info=True)
    sid = str(session_id or "")
    if sid.startswith("chat-"):
        try:
            from core.services.run_follow import begin_follow
            begin_follow(sid, str(run_id or ""))
        except Exception:
            logger.debug("begin_live_turn: begin_follow fejlede", exc_info=True)
        # KRITISK for desk-poller/liveness: registrér i run_event_log (rel). Når
        # server_authoritative_runs er på læser /chat/active-runs + liveness-linjen
        # rel.live_run_ids()/active_run_for_session — IKKE run_follow. Uden dette
        # lyser venstre-panels aktivitets-prik + liveness-linje ALDRIG op for en
        # jarvis-code-tur (selvom follow-token-streamen virker).
        try:
            import core.services.run_event_log as rel
            rel.create(str(run_id or ""), sid)
        except Exception:
            logger.debug("begin_live_turn: rel.create fejlede", exc_info=True)


def end_live_turn(*, session_id: str, run_id: str = "") -> None:
    """Ryd active-run (kun hvis det stadig er DETTE run — undgå at rydde en efterfølger)
    + luk run_follow. Altid safe at kalde, også for et run der aldrig blev registreret."""
    try:
        from core.services.visible_runs_sections.run_control_state import (
            _get_active_visible_run_state,
            _set_active_visible_run,
        )
        state = _get_active_visible_run_state()
        if not run_id or str(state.get("run_id") or "") == str(run_id):
            _set_active_visible_run({"active": False})
    except Exception:
        logger.debug("end_live_turn: active-run clear fejlede", exc_info=True)
    if run_id:
        try:
            import core.services.run_event_log as rel
            rel.mark_done(str(run_id))
        except Exception:
            logger.debug("end_live_turn: rel.mark_done fejlede", exc_info=True)
    sid = str(session_id or "")
    if sid.startswith("chat-"):
        try:
            from core.services.run_follow import end_follow
            end_follow(sid)
        except Exception:
            logger.debug("end_live_turn: end_follow fejlede", exc_info=True)
