"""Experience-episode correction enrichment — closes the negative-signal loop.

Lag-1.5 of the Runtime Decision Policy (added 2026-05-09 alongside Lag 3).

The collector in ``experience_episodes.record_episode`` always writes
``user_corrected=False`` because at write-time we don't know yet
whether Bjørn will correct the previous turn. This listener watches
for correction-phrases in subsequent user messages and back-fills the
flag on the most recent episode in the same session.

Without this enrichment, retrieval substrate would be one-sided
(only positive outcomes) — which would bias Jarvis toward repeating
patterns Bjørn has actually rejected.

Hook: subscribes to ``channel.chat_message_appended`` events and
inspects role='user' messages. If the message matches a correction
phrase AND a recent episode exists in the same session, we mark it
corrected (DB row + chromadb metadata).
"""
from __future__ import annotations

import json
import logging
import re
import threading
from datetime import UTC, datetime, timedelta

logger = logging.getLogger(__name__)

# ───────────────────────────────────────────────────────────────────────
# Correction-phrase detection (Danish + minimal English)
# ───────────────────────────────────────────────────────────────────────

# Match at start of message (case-insensitive). We're conservative:
# rather miss true corrections than mark non-corrections (which would
# bias retrieval against good episodes).
_CORRECTION_PATTERNS: tuple[re.Pattern, ...] = (
    # Direct rejections
    re.compile(r"^\s*nej[,.\s]", re.IGNORECASE),
    re.compile(r"^\s*nope[,.\s]", re.IGNORECASE),
    re.compile(r"^\s*forkert\b", re.IGNORECASE),
    re.compile(r"^\s*det er forkert\b", re.IGNORECASE),
    # Undo / stop
    re.compile(r"\bfortryd\b", re.IGNORECASE),
    re.compile(r"\bstop\s*(det|nu|med)?", re.IGNORECASE),
    re.compile(r"\brul tilbage\b", re.IGNORECASE),
    re.compile(r"\brevert\b", re.IGNORECASE),
    re.compile(r"\bundo\b", re.IGNORECASE),
    # Course-correction phrasings
    re.compile(r"\bdet skal ikke\b", re.IGNORECASE),
    re.compile(r"\bikke s[aå]dan\b", re.IGNORECASE),
    re.compile(r"\bdu mis(forstod|forst[aå]r)\b", re.IGNORECASE),
    re.compile(r"\bdet var ikke\b", re.IGNORECASE),
    re.compile(r"\bglemte du\b", re.IGNORECASE),
    re.compile(r"\bg[oø]r det om\b", re.IGNORECASE),
    re.compile(r"\bprøv igen\b", re.IGNORECASE),
)

# Window in which we associate a correction with the previous turn.
# After this we assume the correction is about something else.
_CORRECTION_WINDOW_MINUTES = 10


def _looks_like_correction(text: str) -> bool:
    """Return True if the message opens with or contains a correction phrase."""
    if not text:
        return False
    head = text.strip()[:240]
    return any(p.search(head) for p in _CORRECTION_PATTERNS)


# ───────────────────────────────────────────────────────────────────────
# Episode-enrichment write
# ───────────────────────────────────────────────────────────────────────


def _mark_recent_episode_corrected(session_id: str) -> str | None:
    """Find the most recent un-corrected episode in this session within
    the time window and mark it as user_corrected.

    Returns the episode_id we touched, or None if nothing matched.
    """
    if not session_id:
        return None
    try:
        from core.runtime.db import connect

        cutoff = (
            datetime.now(UTC) - timedelta(minutes=_CORRECTION_WINDOW_MINUTES)
        ).isoformat()
        with connect() as c:
            row = c.execute(
                """
                SELECT episode_id, outcome_signals_json
                FROM experience_episodes
                WHERE session_id = ?
                  AND created_at >= ?
                  AND user_corrected = 0
                ORDER BY rowid DESC
                LIMIT 1
                """,
                (session_id, cutoff),
            ).fetchone()
            if not row:
                return None

            episode_id = str(row["episode_id"])
            try:
                signals = json.loads(row["outcome_signals_json"] or "{}")
            except Exception:
                signals = {}
            signals["user_corrected_at"] = datetime.now(UTC).isoformat()

            c.execute(
                """
                UPDATE experience_episodes
                SET user_corrected = 1,
                    outcome_signals_json = ?
                WHERE episode_id = ?
                """,
                (json.dumps(signals, ensure_ascii=False), episode_id),
            )
            c.commit()
    except Exception as exc:
        logger.warning("experience_correction: DB update failed: %s", exc)
        return None

    # Mirror the flag in chromadb metadata so retrieval-time view is correct.
    try:
        from core.services.experience_episodes import _get_collection
        collection = _get_collection()
        existing = collection.get(ids=[episode_id], include=["metadatas"])
        metadatas = (existing or {}).get("metadatas") or [None]
        meta = dict(metadatas[0]) if metadatas and metadatas[0] else {}
        meta["user_corrected"] = True
        collection.update(ids=[episode_id], metadatas=[meta])
    except Exception as exc:
        logger.debug("experience_correction: chroma update failed: %s", exc)

    logger.info(
        "experience_correction: marked %s as user_corrected (session=%s)",
        episode_id, session_id,
    )
    return episode_id


# ───────────────────────────────────────────────────────────────────────
# Eventbus listener
# ───────────────────────────────────────────────────────────────────────


_listener_running = False
_listener_thread: threading.Thread | None = None


def _extract_user_message(payload: dict) -> tuple[str, str]:
    """Return (session_id, content) if this is a role=user chat message."""
    if not isinstance(payload, dict):
        return ("", "")
    msg = payload.get("message") or {}
    if not isinstance(msg, dict):
        return ("", "")
    if str(msg.get("role") or "").strip().lower() != "user":
        return ("", "")
    session_id = str(payload.get("session_id") or "").strip()
    content = str(msg.get("content") or "").strip()
    return (session_id, content)


def _listener_loop(q) -> None:
    while _listener_running:
        try:
            item = q.get(timeout=1.0)
        except Exception:
            continue
        if item is None:
            break
        try:
            kind = str(item.get("kind") or "")
            if kind != "channel.chat_message_appended":
                continue
            payload = item.get("payload") or {}
            session_id, content = _extract_user_message(payload)
            if not session_id or not content:
                continue
            if not _looks_like_correction(content):
                continue
            _mark_recent_episode_corrected(session_id)
        except Exception as exc:
            logger.debug("experience_correction: listener error: %s", exc)


def start_listener() -> None:
    """Idempotent — safe to call multiple times."""
    global _listener_running, _listener_thread
    if _listener_running:
        return
    try:
        from core.eventbus.bus import event_bus

        q = event_bus.subscribe()
        _listener_running = True
        _listener_thread = threading.Thread(
            target=_listener_loop,
            args=(q,),
            daemon=True,
            name="experience-correction-listener",
        )
        _listener_thread.start()
        logger.info("experience_correction: listener started")
    except Exception as exc:
        logger.warning("experience_correction: failed to start listener: %s", exc)


def stop_listener() -> None:
    global _listener_running
    _listener_running = False


def build_experience_correction_listener_surface() -> dict[str, object]:
    """Mission Control surface — read-only meta-projection.

    Added during 2026-05-13 coverage push (system_cartographer dark-edge
    closure). Reports module presence so the cartographer registers it as
    observed. Specific state-readers added as the module evolves.
    """
    return {
        "active": True,
        "mode": "experience_correction_listener",
        "summary": "Module loaded; entry points available.",
        "authority": "derived-read-only",
    }


def _emit_experience_correction_listener_event(kind: str, payload: dict[str, object] | None = None) -> None:
    """Emit a scoped event — defensive, never blocks caller.
    Cartographer scans for event_bus.publish() text.
    """
    try:
        from core.eventbus.bus import event_bus
        event_bus.publish(
            f"experience_correction_listener.{kind}",
            payload or {},
        )
    except Exception:
        pass

