"""Dream Carry-Over — hypotheses that survive across sessions.

Extends V2's existing dream_hypothesis_signals + dream_adoption_candidate.
When a dream is "adopted", it gets injected into the next visible prompt.
Confirmation in conversation → confidence up. Disconfirmation → archive.

Persistence: DREAM_CARRY.json in the default workspace runtime dir.
Dreams can deepen over multiple sessions via session_carry_count +
confirmed_sessions. Unconfirmed dreams fade after _FADE_AFTER_SESSIONS.
"""

from __future__ import annotations

import json
import logging
import threading
from datetime import UTC, datetime
from pathlib import Path

from core.eventbus.bus import event_bus
from core.runtime.config import JARVIS_HOME

logger = logging.getLogger(__name__)

_PERSIST_FILE = Path(JARVIS_HOME) / "workspaces" / "default" / "DREAM_CARRY.json"
_LOCK = threading.Lock()
_LOADED = False

_ACTIVE_DREAMS: list[dict[str, object]] = []
_DREAM_ARCHIVE: list[dict[str, object]] = []

_FADE_AFTER_SESSIONS = 5  # unconfirmed dreams archived after this many presentations
_MAX_CONFIDENCE = 0.98
_CONFIRM_BOOST = 0.15
_MULTI_SESSION_CONFIRM_BOOST = 0.08  # additional boost per extra confirmed session


def _ensure_loaded() -> None:
    global _LOADED
    if _LOADED:
        return
    with _LOCK:
        if _LOADED:
            return
        _load()
        _LOADED = True


def _load() -> None:
    global _ACTIVE_DREAMS, _DREAM_ARCHIVE
    try:
        if _PERSIST_FILE.exists():
            data = json.loads(_PERSIST_FILE.read_text(encoding="utf-8"))
            _ACTIVE_DREAMS[:] = list(data.get("active_dreams") or [])
            _DREAM_ARCHIVE[:] = list(data.get("archive") or [])
    except Exception:
        pass


def _save() -> None:
    try:
        _PERSIST_FILE.parent.mkdir(parents=True, exist_ok=True)
        _PERSIST_FILE.write_text(
            json.dumps(
                {"active_dreams": _ACTIVE_DREAMS, "archive": _DREAM_ARCHIVE[-50:]},
                indent=2,
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
    except Exception:
        pass


def adopt_dream(
    *,
    dream_id: str,
    content: str,
    confidence: float = 0.5,
    source_memories: list[str] | None = None,
) -> dict[str, object]:
    """Adopt a dream hypothesis for carry-over to next session."""
    _ensure_loaded()
    now = datetime.now(UTC).isoformat().replace("+00:00", "Z")

    # If already active, preserve session history and boost confidence
    existing = next((d for d in _ACTIVE_DREAMS if d["dream_id"] == dream_id), None)
    if existing:
        existing["content"] = content[:300]
        existing["confidence"] = round(
            min(_MAX_CONFIDENCE, max(float(existing.get("confidence", 0.5)), confidence)),
            2,
        )
        existing["updated_at"] = now
        _save()
        return existing

    dream: dict[str, object] = {
        "dream_id": dream_id,
        "content": content[:300],
        "confidence": round(min(_MAX_CONFIDENCE, max(0.1, confidence)), 2),
        "source_memories": source_memories or [],
        "status": "active",
        "presented": False,
        "confirmed": False,
        "session_carry_count": 0,
        "confirmed_sessions": 0,
        "adopted_at": now,
        "updated_at": now,
    }

    _ACTIVE_DREAMS.append(dream)
    _save()

    event_bus.publish(
        "cognitive_state.dream_adopted",
        {"dream_id": dream_id, "confidence": confidence},
    )
    return dream


def get_presentable_dream() -> dict[str, object] | None:
    """Get the highest-confidence un-presented dream for prompt injection."""
    _ensure_loaded()
    unpresented = [
        d for d in _ACTIVE_DREAMS
        if not d.get("presented") and d.get("status") == "active"
    ]
    if not unpresented:
        return None
    unpresented.sort(key=lambda d: float(d.get("confidence", 0)), reverse=True)
    return unpresented[0]


def mark_dream_presented(dream_id: str) -> None:
    """Mark a dream as presented in the current session; track carry depth."""
    _ensure_loaded()
    for d in _ACTIVE_DREAMS:
        if d["dream_id"] == dream_id:
            d["presented"] = True
            d["session_carry_count"] = int(d.get("session_carry_count") or 0) + 1
            d["updated_at"] = datetime.now(UTC).isoformat().replace("+00:00", "Z")
    _maybe_fade_old_dreams()
    _save()


def confirm_dream(dream_id: str) -> None:
    """Confirm a dream hypothesis — boost confidence, track confirmed sessions."""
    _ensure_loaded()
    for d in _ACTIVE_DREAMS:
        if d["dream_id"] == dream_id:
            confirmed_sessions = int(d.get("confirmed_sessions") or 0) + 1
            d["confirmed"] = True
            d["confirmed_sessions"] = confirmed_sessions
            # Multi-session confirmations give diminishing boosts
            boost = _CONFIRM_BOOST + _MULTI_SESSION_CONFIRM_BOOST * max(0, confirmed_sessions - 1)
            d["confidence"] = round(
                min(_MAX_CONFIDENCE, float(d.get("confidence", 0.5)) + boost), 2
            )
            d["updated_at"] = datetime.now(UTC).isoformat().replace("+00:00", "Z")
            event_bus.publish(
                "cognitive_state.dream_confirmed",
                {
                    "dream_id": dream_id,
                    "confirmed_sessions": confirmed_sessions,
                    "confidence": d["confidence"],
                },
            )
    _save()


def reject_dream(dream_id: str) -> None:
    """Reject a dream hypothesis — archive with 'was_wrong'."""
    _ensure_loaded()
    for d in _ACTIVE_DREAMS:
        if d["dream_id"] == dream_id:
            d["status"] = "was_wrong"
            d["updated_at"] = datetime.now(UTC).isoformat().replace("+00:00", "Z")
            _DREAM_ARCHIVE.append(d)
            event_bus.publish(
                "cognitive_state.dream_rejected",
                {"dream_id": dream_id},
            )
    _ACTIVE_DREAMS[:] = [d for d in _ACTIVE_DREAMS if d["dream_id"] != dream_id]
    _save()


def promote_confirmed_dream_to_identity(dream_id: str) -> dict[str, object] | None:
    """Promote a high-confidence confirmed dream to identity evolution proposal."""
    _ensure_loaded()
    dream = next((d for d in _ACTIVE_DREAMS if d["dream_id"] == dream_id), None)
    if not dream or not dream.get("confirmed"):
        return None
    if float(dream.get("confidence", 0)) < 0.7:
        return None
    try:
        from core.services.contract_evolution import propose_identity_change
        return propose_identity_change(
            target_file="IDENTITY.md",
            proposed_addition=f"Bekræftet indsigt: {dream.get('content', '')[:200]}",
            rationale=f"Dream {dream_id} bekræftet med confidence {dream.get('confidence', 0):.1f}",
            confidence=float(dream.get("confidence", 0.7)),
        )
    except Exception:
        return None


def format_dream_for_prompt(dream: dict[str, object]) -> str:
    """Format a dream for injection into the visible prompt."""
    content = str(dream.get("content") or "")[:200]
    confidence = float(dream.get("confidence", 0.5))
    carry_count = int(dream.get("session_carry_count") or 0)
    confirmed_sessions = int(dream.get("confirmed_sessions") or 0)
    depth_note = ""
    if carry_count >= 2:
        depth_note = f", carried {carry_count} sessions"
    if confirmed_sessions >= 1:
        depth_note += f", confirmed {confirmed_sessions}×"
    return f'[DREAM: "{content}" (confidence: {confidence:.1f}{depth_note})]'


def build_dream_carry_over_surface() -> dict[str, object]:
    _ensure_loaded()
    confirmed = [d for d in _ACTIVE_DREAMS if d.get("confirmed")]
    faded = [d for d in _DREAM_ARCHIVE if d.get("status") == "faded"]
    wrong = [d for d in _DREAM_ARCHIVE if d.get("status") == "was_wrong"]
    deep = [
        d for d in _ACTIVE_DREAMS
        if int(d.get("session_carry_count") or 0) >= 2
    ]
    return {
        "active": bool(_ACTIVE_DREAMS),
        "active_dreams": _ACTIVE_DREAMS,
        "archive": _DREAM_ARCHIVE[-10:],
        "confirmed_count": len(confirmed),
        "faded_count": len(faded),
        "wrong_count": len(wrong),
        "deep_carry_count": len(deep),
        "summary": (
            f"{len(_ACTIVE_DREAMS)} active, {len(confirmed)} confirmed, "
            f"{len(deep)} multi-session, {len(wrong)} wrong"
            if _ACTIVE_DREAMS else "No active dreams"
        ),
    }


def _maybe_fade_old_dreams() -> None:
    """Archive unconfirmed dreams that have been presented too many times."""
    now = datetime.now(UTC).isoformat().replace("+00:00", "Z")
    to_fade = [
        d for d in _ACTIVE_DREAMS
        if not d.get("confirmed")
        and int(d.get("session_carry_count") or 0) >= _FADE_AFTER_SESSIONS
        and d.get("status") == "active"
    ]
    for d in to_fade:
        d["status"] = "faded"
        d["updated_at"] = now
        _DREAM_ARCHIVE.append(d)
        event_bus.publish(
            "cognitive_state.dream_faded",
            {
                "dream_id": d.get("dream_id"),
                "session_carry_count": d.get("session_carry_count"),
            },
        )
    if to_fade:
        _ACTIVE_DREAMS[:] = [d for d in _ACTIVE_DREAMS if d.get("status") == "active"]
