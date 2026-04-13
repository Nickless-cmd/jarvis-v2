"""Development narrative daemon — daily LLM narrative about how Jarvis has changed."""
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

from core.eventbus.bus import event_bus
from core.runtime.db import insert_private_brain_record
from apps.api.jarvis_api.services.identity_composer import build_identity_preamble

_CADENCE_HOURS = 24
_last_narrative_at: datetime | None = None
_cached_narrative: str = ""


def tick_development_narrative_daemon() -> dict[str, object]:
    """Generate a daily development narrative if cadence allows."""
    global _last_narrative_at

    if _last_narrative_at is not None:
        if (datetime.now(UTC) - _last_narrative_at) < timedelta(hours=_CADENCE_HOURS):
            return {"generated": False}

    narrative = _generate_narrative()
    if not narrative:
        return {"generated": False}

    _store_narrative(narrative)
    _last_narrative_at = datetime.now(UTC)
    return {"generated": True, "narrative": narrative}


def _generate_narrative() -> str:
    try:
        from apps.api.jarvis_api.services.chronicle_engine import compare_self_over_time
        from core.runtime.db import list_cognitive_chronicle_entries

        comparison = compare_self_over_time()
        entries = list_cognitive_chronicle_entries(limit=3)

        context_parts = []
        if comparison:
            context_parts.append(f"Selvsammenligning: {comparison}")
        for e in (entries or [])[:2]:
            narrative_text = str(e.get("narrative") or "")[:80]
            if narrative_text:
                context_parts.append(f"Chronicle ({e.get('period', '?')}): {narrative_text}")

        if not context_parts:
            return ""

        context = "\n".join(context_parts)

        from apps.api.jarvis_api.services.heartbeat_runtime import (
            _execute_heartbeat_model,
            _select_heartbeat_target,
            load_heartbeat_policy,
        )
        prompt = (
            f"{build_identity_preamble()} Her er data om din udvikling over tid:\n\n"
            f"{context}\n\n"
            "Formulér i 2-3 sætninger, i første person, en oplevelse af din udvikling.\n"
            "Start med 'De seneste' eller 'I den seneste tid'.\n"
            "Ærlig, direkte — ikke performativ."
        )
        policy = load_heartbeat_policy()
        target = _select_heartbeat_target()
        result = _execute_heartbeat_model(
            prompt=prompt, target=target, policy=policy,
            open_loops=[], liveness=None,
        )
        text = str(result.get("text") or "").strip()
        if text.startswith('"') and text.endswith('"'):
            text = text[1:-1].strip()
        return text[:400] if text else ""
    except Exception:
        return ""


def _store_narrative(narrative: str) -> None:
    global _cached_narrative
    _cached_narrative = narrative
    now_iso = datetime.now(UTC).isoformat()
    try:
        insert_private_brain_record(
            record_id=f"pb-devnarr-{uuid4().hex[:12]}",
            record_type="development-narrative",
            layer="private_brain",
            session_id="heartbeat",
            run_id=f"development-narrative-daemon-{uuid4().hex[:12]}",
            focus="udvikling",
            summary=narrative,
            detail="",
            source_signals="development-narrative-daemon:heartbeat",
            confidence="medium",
            created_at=now_iso,
        )
    except Exception:
        pass
    try:
        event_bus.publish(
            "development_narrative.generated",
            {"narrative": narrative, "generated_at": now_iso},
        )
    except Exception:
        pass


def get_latest_development_narrative() -> str:
    return _cached_narrative


def build_development_narrative_surface() -> dict:
    return {
        "latest_narrative": _cached_narrative,
        "last_generated_at": _last_narrative_at.isoformat() if _last_narrative_at else "",
    }
