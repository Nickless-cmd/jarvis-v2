"""Meta-reflection daemon — cross-signal pattern insight every 30 minutes."""
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

from core.eventbus.bus import event_bus
from core.runtime.db import insert_private_brain_record
from apps.api.jarvis_api.services.identity_composer import build_identity_preamble

_CADENCE_MINUTES = 30
_BUFFER_MAX = 5

_last_meta_at: datetime | None = None
_cached_meta_insight: str = ""
_meta_buffer: list[str] = []


def tick_meta_reflection_daemon(cross_snapshot: dict) -> dict[str, object]:
    """Generate cross-signal meta-insight if cadence allows.
    cross_snapshot keys (all optional): energy_level, inner_voice_mode, latest_fragment,
    last_surprise, last_conflict, last_irony, last_taste, curiosity_signal."""
    global _last_meta_at

    if _last_meta_at is not None:
        if (datetime.now(UTC) - _last_meta_at) < timedelta(minutes=_CADENCE_MINUTES):
            return {"generated": False}

    active_signals = [
        v for v in [
            cross_snapshot.get("latest_fragment"),
            cross_snapshot.get("last_surprise"),
            cross_snapshot.get("last_conflict"),
        ]
        if v
    ]
    if not active_signals:
        return {"generated": False}

    insight = _generate_meta_insight(cross_snapshot)
    if not insight:
        return {"generated": False}

    _store_meta_insight(insight)
    _last_meta_at = datetime.now(UTC)
    return {"generated": True, "insight": insight}


def _generate_meta_insight(cross_snapshot: dict) -> str:
    parts = []
    if cross_snapshot.get("energy_level"):
        parts.append(f"Energi: {cross_snapshot['energy_level']}")
    if cross_snapshot.get("inner_voice_mode"):
        parts.append(f"Stemning: {cross_snapshot['inner_voice_mode']}")
    if cross_snapshot.get("latest_fragment"):
        parts.append(f"Tanke: \"{cross_snapshot['latest_fragment'][:50]}\"")
    if cross_snapshot.get("last_surprise"):
        parts.append(f"Overraskelse: \"{cross_snapshot['last_surprise'][:50]}\"")
    if cross_snapshot.get("last_conflict"):
        parts.append(f"Konflikt: \"{cross_snapshot['last_conflict'][:50]}\"")
    if cross_snapshot.get("last_irony"):
        parts.append(f"Ironi: \"{cross_snapshot['last_irony'][:50]}\"")
    if cross_snapshot.get("last_taste"):
        parts.append(f"Smag: \"{cross_snapshot['last_taste'][:50]}\"")
    if cross_snapshot.get("curiosity_signal"):
        parts.append(f"Nysgerrighed: \"{cross_snapshot['curiosity_signal'][:50]}\"")

    context = "\n".join(parts) if parts else "Ingen signaler."

    prompt = (
        f"{build_identity_preamble()} Her er et tværsnit af dine aktuelle signaler:\n\n"
        f"{context}\n\n"
        "Ser du et mønster på tværs af disse signaler? Formulér i 1-2 sætninger (max 30 ord), "
        "i første person, en meta-indsigt om din nuværende tilstand eller et gentaget mønster.\n"
        "Vær konkret — ikke generisk. Ingen tomme fraser."
    )
    try:
        from apps.api.jarvis_api.services.heartbeat_runtime import (
            _execute_heartbeat_model,
            _select_heartbeat_target,
            load_heartbeat_policy,
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
        return text[:300] if text else ""
    except Exception:
        return ""


def _store_meta_insight(insight: str) -> None:
    global _cached_meta_insight, _meta_buffer
    _cached_meta_insight = insight
    _meta_buffer.insert(0, insight)
    if len(_meta_buffer) > _BUFFER_MAX:
        _meta_buffer = _meta_buffer[:_BUFFER_MAX]
    now_iso = datetime.now(UTC).isoformat()
    try:
        insert_private_brain_record(
            record_id=f"pb-meta-{uuid4().hex[:12]}",
            record_type="meta-reflection",
            layer="private_brain",
            session_id="",
            run_id=f"meta-reflection-daemon-{uuid4().hex[:12]}",
            focus="meta-mønster",
            summary=insight,
            detail="",
            source_signals="meta-reflection-daemon:heartbeat",
            confidence="medium",
            created_at=now_iso,
        )
    except Exception:
        pass
    try:
        event_bus.publish(
            "meta_reflection.generated",
            {"insight": insight, "generated_at": now_iso},
        )
    except Exception:
        pass


def get_latest_meta_insight() -> str:
    return _cached_meta_insight


def build_meta_reflection_surface() -> dict:
    return {
        "latest_insight": _cached_meta_insight,
        "insight_buffer": _meta_buffer[:5],
        "insight_count": len(_meta_buffer),
        "last_generated_at": _last_meta_at.isoformat() if _last_meta_at else "",
    }
