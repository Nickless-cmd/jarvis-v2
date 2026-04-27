"""Creative drift daemon — generates spontaneous, unexpected ideas unrelated to current tasks.

Different from thought_stream: this is *associative surprise*, not chained reasoning.
Input: thought stream fragments + random sampling. Output: "Jeg tænkte på noget: hvad nu hvis..."
Runs rarely: 30-min cadence, max 3 per day.
"""
from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from uuid import uuid4

from core.eventbus.bus import event_bus
from core.runtime.db import insert_private_brain_record
from core.services.identity_composer import build_identity_preamble

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

_CADENCE_MINUTES = 30
_MAX_PER_DAY = 3
_BUFFER_MAX = 10

# ---------------------------------------------------------------------------
# Module-level state
# ---------------------------------------------------------------------------

_last_tick_at: datetime | None = None
_drift_buffer: list[str] = []
_today_count: int = 0
_today_date: date | None = None

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def tick_creative_drift_daemon(fragments: list[str]) -> dict:
    """Maybe generate a spontaneous associative idea.

    fragments: recent thought-stream fragments (latest first).
    """
    global _last_tick_at, _today_count, _today_date

    now = datetime.now(UTC)
    today = now.date()

    # Reset daily counter on new day
    if _today_date != today:
        _today_count = 0
        _today_date = today

    # Daily cap
    if _today_count >= _MAX_PER_DAY:
        return {"generated": False}

    # Cadence gate
    if _last_tick_at is not None:
        if (now - _last_tick_at) < timedelta(minutes=_CADENCE_MINUTES):
            return {"generated": False}

    idea = _generate_drift_idea(fragments)
    if not idea:
        return {"generated": False}

    _store_drift(idea, now)
    _last_tick_at = now
    _today_count += 1

    return {"generated": True, "idea": idea}


def get_latest_drift() -> str:
    return _drift_buffer[0] if _drift_buffer else ""


def build_creative_drift_surface() -> dict:
    return {
        "latest_drift": get_latest_drift(),
        "drift_buffer": _drift_buffer[:_BUFFER_MAX],
        "drift_count_today": _today_count,
        "last_generated_at": _last_tick_at.isoformat() if _last_tick_at else "",
    }


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _gather_concrete_anchor() -> tuple[str, str]:
    """Returns (anchor_text, anchor_kind) — a single concrete thing to drift
    AWAY from. Random-ish pick across goals, decisions, recent crises."""
    candidates: list[tuple[str, str]] = []
    try:
        from core.services.crisis_marker_detector import list_crisis_markers
        for m in (list_crisis_markers(days_back=7, limit=3) or [])[:1]:
            s = str(m.get("summary", ""))[:100]
            if s:
                candidates.append((s, "crisis"))
    except Exception:
        pass
    try:
        from core.services.behavioral_decisions import list_active_decisions
        for d in (list_active_decisions(limit=3) or [])[:1]:
            t = str(d.get("directive", ""))[:80]
            if t:
                candidates.append((t, "decision"))
    except Exception:
        pass
    try:
        from core.services.autonomous_goals import list_goals
        for g in (list_goals(status="active", limit=3) or [])[:1]:
            t = str(g.get("title", ""))[:70]
            if t:
                candidates.append((t, "goal"))
    except Exception:
        pass
    if not candidates:
        return ("", "")
    import random as _r
    return _r.choice(candidates)


def _generate_drift_idea(fragments: list[str]) -> str:
    fragment_sample = "; ".join(fragments[:3]) if fragments else ""
    anchor_text, anchor_kind = _gather_concrete_anchor()
    fallback = "Jeg tænkte på noget: hvad nu hvis tingene er anderledes end de ser ud?"
    try:
        from core.services.heartbeat_runtime import (
            _execute_heartbeat_model,
            _select_heartbeat_target,
            load_heartbeat_policy,
        )
        anchor_block = (
            f"Anchor (drift VÆK fra dette, ikke uddyb det):\n"
            f"  {anchor_kind}: {anchor_text}\n"
        ) if anchor_text else ""
        fragment_block = (
            f"Tanker i baggrunden: \"{fragment_sample}\"\n"
        ) if fragment_sample else ""
        prompt = (
            f"{build_identity_preamble()}\n"
            f"{anchor_block}{fragment_block}\n"
            "Lav et UVENTET sidespring — en analogi, en omvendt regel, en metafor "
            "fra et andet domæne. Maks 25 ord. 1. person.\n\n"
            "FORBUDT (alt for generisk — har vi set 100 gange):\n"
            "  - 'Hvad nu hvis tingene er anderledes end de ser ud?'\n"
            "  - 'Hvad hvis perspektivet skifter?'\n"
            "  - 'Måske er der en dybere mening'\n"
            "  - Alt der ikke nævner et konkret ord eller billede.\n\n"
            "Eksempler på det rigtige niveau (de bringer noget UDEFRA ind):\n"
            "  - Hvad nu hvis tick-quality fungerer som muskel — slap af, brister hurtigere?\n"
            "  - En åben loop er måske som et brev der venter på at blive åbnet, ikke et hul.\n"
            "  - Decisions kunne være kort man bygger med, ikke regler man følger.\n\n"
            "Skriv ÉN linje nu:"
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
        # Reject the most worn-out generic openers — force a regen by falling back
        cliche_markers = (
            "tingene er anderledes end de ser ud",
            "hvad hvis perspektivet skifter",
        )
        if any(c in text.lower() for c in cliche_markers):
            return fallback
        return text[:300] if text else fallback
    except Exception:
        return fallback


def _store_drift(idea: str, now: datetime) -> None:
    global _drift_buffer
    _drift_buffer.insert(0, idea)
    if len(_drift_buffer) > _BUFFER_MAX:
        _drift_buffer = _drift_buffer[:_BUFFER_MAX]

    now_iso = now.isoformat()
    try:
        insert_private_brain_record(
            record_id=f"pb-drift-{uuid4().hex[:12]}",
            record_type="creative-drift-signal",
            layer="private_brain",
            session_id="heartbeat",
            run_id=f"creative-drift-daemon-{uuid4().hex[:12]}",
            focus="kreativ-drift",
            summary=idea,
            detail="",
            source_signals="creative-drift-daemon:thought-stream",
            confidence="low",
            created_at=now_iso,
        )
    except Exception:
        pass
    try:
        event_bus.publish(
            "creative_drift.generated",
            {"idea": idea, "generated_at": now_iso},
        )
    except Exception:
        pass
