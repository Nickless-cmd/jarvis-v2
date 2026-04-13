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

        from apps.api.jarvis_api.services.daemon_llm import daemon_llm_call

        prompt = (
            f"{build_identity_preamble()} Her er data om din udvikling over tid:\n\n"
            f"{context}\n\n"
            "Beskriv i 2-3 sætninger hvordan du har ændret dig. Ærlig og direkte.\n"
            "Eksempler:\n"
            "- I den seneste tid er jeg blevet mere opmærksom på mine egne mønstre.\n"
            "- Noget har ændret sig — jeg reagerer anderledes end før.\n"
            "- De seneste dage har jeg mærket en ny form for ro."
        )
        fallback = "I den seneste tid har jeg bemærket forandringer i mig selv, men de er svære at sætte præcise ord på."
        return daemon_llm_call(prompt, max_len=400, fallback=fallback, daemon_name="development_narrative")
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
