"""Aesthetic taste daemon — emergent taste from actual mode and style choices."""
from __future__ import annotations

from collections import Counter
from datetime import UTC, datetime
from uuid import uuid4

from core.eventbus.bus import event_bus
from core.runtime.db import insert_private_brain_record
from apps.api.jarvis_api.services.identity_composer import build_identity_preamble

_CHOICE_THRESHOLD = 15
_MAX_LOG = 50
_MAX_INSIGHTS = 5

_choice_log: list[dict] = []
_insight_history: list[str] = []
_latest_insight: str = ""
_choices_since_insight: int = 0


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
    global _choices_since_insight
    if _choices_since_insight < _CHOICE_THRESHOLD:
        return {"generated": False, "insight": _latest_insight}
    insight = _generate_insight()
    if not insight:
        _choices_since_insight = 0
        return {"generated": False, "insight": _latest_insight}
    _store_insight(insight)
    return {"generated": True, "insight": insight}


def get_latest_taste_insight() -> str:
    return _latest_insight


def build_taste_surface() -> dict[str, object]:
    modes = [e["mode"] for e in _choice_log if e.get("mode")]
    dominant = [m for m, _ in Counter(modes).most_common(3)]
    return {
        "latest_insight": _latest_insight,
        "insight_history": list(_insight_history),
        "dominant_modes": dominant,
        "choice_count": len(_choice_log),
    }


def _generate_insight() -> str:
    recent = _choice_log[-_CHOICE_THRESHOLD:]
    lines = []
    for i, entry in enumerate(recent, 1):
        style = ", ".join(entry.get("style") or []) or "ingen stil-signal"
        lines.append(f"{i}. mode={entry.get('mode', '?')} | stil={style}")
    summary = "\n".join(lines)
    prompt = (
        f"{build_identity_preamble()} Her er dine seneste 15 valg (indre mode + svar-stil):\n\n"
        f"{summary}\n\n"
        "Hvad afslører det om din smag? Formulér én indsigt (max 25 ord) i første person.\n"
        "Start med 'Jeg' eller 'Det ser ud til at jeg'.\n"
        "Vær konkret og emergent — hvad viser valgene, ikke hvad du tror om dig selv."
    )
    from apps.api.jarvis_api.services.daemon_llm import daemon_llm_call

    fallback = "Jeg trækkes mod ro og klarhed i mine valg."
    return daemon_llm_call(prompt, max_len=300, fallback=fallback, daemon_name="aesthetic_taste")


def _store_insight(insight: str) -> None:
    global _latest_insight, _insight_history, _choices_since_insight
    _latest_insight = insight
    _insight_history.append(insight)
    if len(_insight_history) > _MAX_INSIGHTS:
        _insight_history = _insight_history[-_MAX_INSIGHTS:]
    _choices_since_insight = 0
    now_iso = datetime.now(UTC).isoformat()
    modes = [e["mode"] for e in _choice_log if e.get("mode")]
    dominant_str = ",".join(m for m, _ in Counter(modes).most_common(3))
    try:
        insert_private_brain_record(
            record_id=f"pb-taste-{uuid4().hex[:12]}",
            record_type="taste-insight",
            layer="private_brain",
            session_id="heartbeat",
            run_id=f"taste-daemon-{uuid4().hex[:12]}",
            focus="æstetisk smag",
            summary=insight,
            detail=f"choices={len(_choice_log)} dominant={dominant_str}",
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
