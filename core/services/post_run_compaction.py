"""Luk kontekst-budgettet igen efter en lang synlig tur.

En baggrundskomprimering kan afslutte midt i en agentisk tur. Markoeren er da
korrekt og mindre, men turen kan bagefter skrive mange nye tool-resultater og
assistentsvar efter markoeren. Auto-compaction bliver normalt kun vurderet ved
naeste prompt-build; uden en ny brugerbesked kan composer-ringen derfor staa
roed, selv om turen allerede er slut.

Denne lille subscriber vurderer den samme autoritative prompt-overflade, naar
det afsluttende assistant-message er gemt. Den genbruger den eksisterende
compaction-policy og starter kun arbejdet, hvis det levende attention-budget
faktisk er overskredet.
"""
from __future__ import annotations

import logging
import queue
import threading
from typing import Any

logger = logging.getLogger(__name__)

_stop = threading.Event()
_thread: threading.Thread | None = None
_subscriber: queue.Queue[dict[str, Any] | None] | None = None


def _completed_visible_session(event: dict[str, Any]) -> str:
    """Session-id for et gemt, afsluttende visible-run-svar — ellers ``""``."""
    if str(event.get("kind") or "") != "channel.chat_message_appended":
        return ""
    payload = event.get("payload") or {}
    if not isinstance(payload, dict) or str(payload.get("source") or "") != "visible-run":
        return ""
    message = payload.get("message") or {}
    if not isinstance(message, dict) or str(message.get("role") or "") != "assistant":
        return ""
    return str(payload.get("session_id") or message.get("session_id") or "").strip()


def compact_after_completed_turn(session_id: str) -> bool:
    """Vurdér og evt. start den normale compaction for den afsluttede session.

    Returnerer om sessionen gik fra ikke-inflight til inflight. Funktionen
    gætter ikke ud fra compaction-loggen: den bygger samme transcript som en
    rigtig prompt, men med ``bivirkninger=False``, og afleverer det derefter til
    den eksisterende policy.
    """
    sid = str(session_id or "").strip()
    if not sid:
        return False
    from core.runtime.settings import load_settings
    from core.services import prompt_contract as pc

    messages = pc._build_structured_transcript_messages(
        sid, limit=60, include=True, bivirkninger=False,
    )
    if not messages:
        return False
    before = sid in pc._compact_inflight
    pc._maybe_auto_compact_session(sid, messages, load_settings())
    return not before and sid in pc._compact_inflight


def _handle(event: dict[str, Any]) -> None:
    sid = _completed_visible_session(event)
    if not sid:
        return
    try:
        if compact_after_completed_turn(sid):
            logger.info("post-run compaction startet for session=%s", sid)
    except Exception:
        # Et eftertjek maa aldrig kunne skade den tur der allerede er gemt.
        logger.warning("post-run compaction-tjek fejlede for session=%s", sid, exc_info=True)


def _loop(subscriber: queue.Queue[dict[str, Any] | None]) -> None:
    while not _stop.is_set():
        try:
            event = subscriber.get(timeout=0.5)
        except queue.Empty:  # Normal timeout: giver stop-flaget en fast responstid.
            continue
        if event is None:
            break
        _handle(event)


def _catch_up_recent_sessions() -> None:
    """Efter en genstart: eftertjek få nyligt afsluttede sessioner én gang."""
    try:
        from core.eventbus.bus import event_bus

        sessions: list[str] = []
        for event in event_bus.recent(limit=500):
            sid = _completed_visible_session(event)
            if sid and sid not in sessions:
                sessions.append(sid)
            if len(sessions) >= 8:
                break
        for sid in sessions:
            compact_after_completed_turn(sid)
    except Exception:
        logger.warning("post-run compaction catch-up fejlede", exc_info=True)


def start_post_run_compaction() -> None:
    """Start subscriber + et asynkront catch-up. Idempotent."""
    global _thread, _subscriber
    if _thread and _thread.is_alive():
        return
    from core.eventbus.bus import event_bus

    _stop.clear()
    _subscriber = event_bus.subscribe()
    _thread = threading.Thread(
        target=_loop, args=(_subscriber,), name="post-run-compaction", daemon=True,
    )
    _thread.start()
    threading.Thread(
        target=_catch_up_recent_sessions, name="post-run-compaction-catch-up", daemon=True,
    ).start()


def stop_post_run_compaction() -> None:
    global _thread, _subscriber
    _stop.set()
    if _subscriber is not None:
        from core.eventbus.bus import event_bus
        event_bus.unsubscribe(_subscriber)
    if _thread and _thread.is_alive():
        _thread.join(timeout=1.0)
    _thread = None
    _subscriber = None
