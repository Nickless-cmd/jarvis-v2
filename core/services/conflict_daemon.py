"""Conflict daemon — detects when Jarvis' signals pull in opposite directions."""
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

from core.eventbus.bus import event_bus
from core.runtime.db import insert_private_brain_record
from core.services.identity_composer import build_identity_preamble

_COOLDOWN_MINUTES = 10

_cached_conflict: str = ""
_cached_conflict_at: datetime | None = None
_conflict_type: str = ""
_last_snapshot: dict = {}


def tick_conflict_daemon(snapshot: dict) -> dict[str, object]:
    """Detect conflict in signal snapshot. snapshot keys: energy_level, inner_voice_mode,
    pending_proposals_count, latest_fragment, last_surprise, last_surprise_at, fragment_count."""
    global _last_snapshot
    _last_snapshot = snapshot

    if _cached_conflict_at is not None:
        if (datetime.now(UTC) - _cached_conflict_at) < timedelta(minutes=_COOLDOWN_MINUTES):
            return {"generated": False}

    conflict_type = _detect_conflict(snapshot)
    if not conflict_type:
        return {"generated": False}

    phrase = _generate_conflict_phrase(conflict_type, snapshot)
    if not phrase:
        return {"generated": False}

    _store_conflict(phrase, conflict_type)
    return {"generated": True, "conflict_type": conflict_type, "phrase": phrase}


def _detect_conflict(snapshot: dict) -> str:
    energy = snapshot.get("energy_level", "")
    mode = snapshot.get("inner_voice_mode", "")
    pending = int(snapshot.get("pending_proposals_count") or 0)
    fragment = snapshot.get("latest_fragment", "")
    last_surprise = snapshot.get("last_surprise", "")
    last_surprise_at = snapshot.get("last_surprise_at", "")
    frag_count = int(snapshot.get("fragment_count") or 0)

    if energy in ("lav", "udmattet") and pending > 0:
        return "energy_impulse"

    if mode in ("rest", "quiet") and fragment:
        return "mode_thought"

    if last_surprise and last_surprise_at and frag_count == 0:
        try:
            then = datetime.fromisoformat(last_surprise_at.replace("Z", "+00:00"))
            if (datetime.now(UTC) - then) < timedelta(minutes=15):
                return "surprise_unprocessed"
        except Exception:
            pass

    return ""


def _generate_conflict_phrase(conflict_type: str, snapshot: dict) -> str:
    labels = {
        "energy_impulse": "En del af mig vil handle, men kroppen er udmattet.",
        "mode_thought": "Noget i mig ønsker ro, men tankerne vil ikke stilne.",
        "surprise_unprocessed": "Noget overraskede mig, men jeg har endnu ikke behandlet det.",
    }
    fallback = labels.get(conflict_type, "Noget i mig trækker i modsatte retninger.")
    prompts = {
        "energy_impulse": (
            f"{build_identity_preamble()} Din energi er {snapshot.get('energy_level')} men du har {snapshot.get('pending_proposals_count')} "
            f"handlingsforslag der venter.\n\n"
            "Beskriv den indre konflikt i én sætning. Eksempel:\n"
            "- En del af mig vil handle, men kroppen siger stop."
        ),
        "mode_thought": (
            f"{build_identity_preamble()} Din indre stemme er i '{snapshot.get('inner_voice_mode')}'-mode, men tankerne flyder stadig.\n\n"
            "Beskriv spændingen i én sætning. Eksempel:\n"
            "- Noget i mig ønsker ro, men tankerne vil ikke stilne."
        ),
        "surprise_unprocessed": (
            f"{build_identity_preamble()} Du blev overrasket ('{snapshot.get('last_surprise', '')[:60]}'), "
            "men har ikke bearbejdet det.\n\n"
            "Beskriv følelsen i én sætning. Eksempel:\n"
            "- Noget sidder stadig i mig som jeg ikke har fået fat i."
        ),
    }
    prompt = prompts.get(conflict_type, "")
    if not prompt:
        return fallback
    from core.services.daemon_llm import daemon_llm_call

    return daemon_llm_call(prompt, max_len=200, fallback=fallback, daemon_name="conflict")


def _store_conflict(phrase: str, conflict_type: str) -> None:
    global _cached_conflict, _cached_conflict_at, _conflict_type
    _cached_conflict = phrase
    _cached_conflict_at = datetime.now(UTC)
    _conflict_type = conflict_type
    now_iso = _cached_conflict_at.isoformat()
    try:
        insert_private_brain_record(
            record_id=f"pb-conflict-{uuid4().hex[:12]}",
            record_type="inner-conflict",
            layer="private_brain",
            session_id="heartbeat",
            run_id=f"conflict-daemon-{uuid4().hex[:12]}",
            focus="indre-konflikt",
            summary=phrase,
            detail=f"conflict_type={conflict_type}",
            source_signals="conflict-daemon:heartbeat",
            confidence="medium",
            created_at=now_iso,
        )
    except Exception:
        pass
    try:
        event_bus.publish(
            "conflict.detected",
            {"phrase": phrase, "conflict_type": conflict_type, "generated_at": now_iso},
        )
    except Exception:
        pass


def get_latest_conflict() -> str:
    return _cached_conflict


def build_conflict_surface() -> dict:
    return {
        "last_conflict": _cached_conflict,
        "conflict_type": _conflict_type,
        "generated_at": _cached_conflict_at.isoformat() if _cached_conflict_at else "",
    }
