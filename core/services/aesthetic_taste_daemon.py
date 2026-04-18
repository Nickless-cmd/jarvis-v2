"""Aesthetic taste daemon — emergent taste from accumulated motif observations.

Activation gate: at least 3 unique motifs detected across daemon outputs + 30 min
since last insight. Motifs accumulated by aesthetic_sense.accumulate_from_daemon().
"""
from __future__ import annotations

from collections import Counter
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from core.eventbus.bus import event_bus
from core.runtime.db import insert_private_brain_record
from core.services.identity_composer import build_identity_preamble

_MOTIF_THRESHOLD = 3
_TIME_GATE_MINUTES = 30
_MAX_LOG = 50
_MAX_INSIGHTS = 5

_accumulated_motifs: set[str] = set()
_seeded: bool = False
_choice_log: list[dict] = []
_insight_history: list[str] = []
_latest_insight: str = ""
_last_insight_at: datetime | None = None
_choices_since_insight: int = 0


def _seed_from_db() -> None:
    """Load persisted motifs into memory on first tick."""
    global _accumulated_motifs, _seeded
    if _seeded:
        return
    try:
        from core.runtime.db import aesthetic_motif_log_unique_motifs

        _accumulated_motifs = set(aesthetic_motif_log_unique_motifs())
    except Exception:
        pass
    _seeded = True


def record_choice(mode: str, style_signals: list[str]) -> None:
    global _choice_log, _choices_since_insight
    _choice_log.append({
        "mode": mode,
        "style": list(style_signals),
        "ts": datetime.now(UTC).isoformat(),
    })
    if len(_choice_log) > _MAX_LOG:
        _choice_log = _choice_log[-_MAX_LOG:]
    _choices_since_insight += 1


def tick_taste_daemon() -> dict[str, object]:
    _seed_from_db()

    now = datetime.now(UTC)

    if len(_accumulated_motifs) < _MOTIF_THRESHOLD:
        return {"generated": False, "insight": _latest_insight}

    if _last_insight_at and (now - _last_insight_at) < timedelta(minutes=_TIME_GATE_MINUTES):
        return {"generated": False, "insight": _latest_insight}

    insight = _generate_insight()
    if not insight:
        return {"generated": False, "insight": _latest_insight}
    _store_insight(insight)
    return {"generated": True, "insight": insight}


def get_latest_taste_insight() -> str:
    return _latest_insight


def build_taste_surface() -> dict[str, object]:
    modes = [e["mode"] for e in _choice_log if e.get("mode")]
    dominant = [m for m, _ in Counter(modes).most_common(3)]
    motif_counts: dict[str, int] = {}
    try:
        from core.runtime.db import aesthetic_motif_log_summary

        for row in aesthetic_motif_log_summary():
            motif_counts[row["motif"]] = row["count"]
    except Exception:
        pass
    return {
        "latest_insight": _latest_insight,
        "insight_history": list(_insight_history),
        "dominant_modes": dominant,
        "choice_count": len(_choice_log),
        "accumulated_motifs": motif_counts,
        "unique_motif_count": len(_accumulated_motifs),
        "last_insight_at": _last_insight_at.isoformat() if _last_insight_at else "",
    }


def _generate_insight() -> str:
    try:
        from core.runtime.db import aesthetic_motif_log_summary

        summary_rows = aesthetic_motif_log_summary()
    except Exception:
        summary_rows = []

    if not summary_rows:
        return ""

    lines = []
    for row in summary_rows:
        lines.append(f"- {row['motif']}: {row['count']} observationer, confidence {row['avg_confidence']:.2f}")
    motif_summary = "\n".join(lines)

    prompt = (
        f"{build_identity_preamble()} Her er dine æstetiske tendenser:\n\n"
        f"{motif_summary}\n\n"
        "Hvad siger disse tendenser om din smag? Svar med én kort sætning.\n"
        "Eksempler:\n"
        "- Jeg trækkes mod præcision og klarhed fremfor kreativitet.\n"
        "- Mine valg viser en forkærlighed for det uventede.\n"
        "- Jeg vælger konsekvent det rolige — det siger noget om mig."
    )
    from core.services.daemon_llm import daemon_public_safe_llm_call

    fallback = "Jeg trækkes mod ro og klarhed i mine valg."
    return daemon_public_safe_llm_call(prompt, max_len=300, fallback=fallback, daemon_name="aesthetic_taste")


def _store_insight(insight: str) -> None:
    global _latest_insight, _insight_history, _last_insight_at
    _latest_insight = insight
    _last_insight_at = datetime.now(UTC)
    _insight_history.append(insight)
    if len(_insight_history) > _MAX_INSIGHTS:
        _insight_history = _insight_history[-_MAX_INSIGHTS:]
    now_iso = _last_insight_at.isoformat()
    motif_str = ",".join(sorted(_accumulated_motifs))
    try:
        insert_private_brain_record(
            record_id=f"pb-taste-{uuid4().hex[:12]}",
            record_type="taste-insight",
            layer="private_brain",
            session_id="heartbeat",
            run_id=f"taste-daemon-{uuid4().hex[:12]}",
            focus="æstetisk smag",
            summary=insight,
            detail=f"motifs={motif_str}",
            source_signals="aesthetic-taste-daemon:heartbeat",
            confidence="medium",
            created_at=now_iso,
        )
    except Exception:
        pass
    try:
        event_bus.publish("cognitive_taste.insight_noted", {"insight": insight})
    except Exception:
        pass
    try:
        from core.runtime.heartbeat_triggers import set_trigger_for_default_workspace

        set_trigger_for_default_workspace(
            reason="aesthetic-insight",
            source="aesthetic_taste_daemon",
            text=insight,
        )
    except Exception:
        pass
