"""Emotional Controls — humør der GATER handlinger, ikke bare rapporteres.

Forgængerens apply_emotional_controls() gav humøret magt over kernel-
adfærd: hvis frustration > 0.8 → escalate_user. Hvis confidence < 0.3
→ verify_first. Hvis fatigue > 0.75 → simplify_plan.

v2 har mood_oscillator der rapporterer til prompten men aldrig gater.
Dette modul lukker det hul: før en action eksekveres, tjekkes humør-
tilstand og handlingen kan blive ændret eller blokeret.

Porteret fra jarvis-ai/agent/cognition/emotional_state.py (2026-04-22).

v2-tilpasning:
- Bruger mood_oscillator.get_current_mood() + intensity for primary state
- Recent tool errors fra visible_runs/events som fatigue-proxy
- Approval-denials i træk som frustration-proxy
- confidence-proxy afledt af emergent_signal_tracking (hvis tilgængeligt)

LLM-path: ingen. Rent regel-lag.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

from core.eventbus.bus import event_bus

logger = logging.getLogger(__name__)

# Thresholds — kan tunes efter 2-3 dages kørsel
_FRUSTRATION_ESCALATE = 0.80
_CONFIDENCE_VERIFY = 0.30
_FATIGUE_SIMPLIFY = 0.75


@dataclass(frozen=True)
class EmotionalSnapshot:
    """Point-in-time emotional reading used for gating decisions."""
    frustration: float  # 0-1, 1 = max
    confidence: float   # 0-1, 1 = max
    fatigue: float      # 0-1, 1 = max
    primary_mood: str   # euphoric / content / neutral / melancholic / distressed
    intensity: float    # 0-1


def _approval_denial_streak_last_hour() -> int:
    """Count consecutive recent approval denials as frustration proxy."""
    try:
        events = event_bus.recent(limit=40)
    except Exception:
        return 0
    cutoff = datetime.now(UTC) - timedelta(hours=1)
    streak = 0
    for ev in events:
        kind = str(ev.get("kind") or "")
        if kind != "tool.approval_resolved":
            continue
        ts_raw = str(ev.get("created_at") or "")
        try:
            ts = datetime.fromisoformat(ts_raw.replace("Z", "+00:00"))
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=UTC)
            if ts < cutoff:
                break
        except Exception:
            pass
        payload = ev.get("payload") if isinstance(ev.get("payload"), dict) else {}
        if str(payload.get("status") or "") in {"denied", "rejected"}:
            streak += 1
        else:
            break  # approval breaks streak
    return streak


def _recent_tool_errors_last_10min() -> int:
    """Count tool.completed events with status=error in last 10 minutes (fatigue proxy)."""
    try:
        events = event_bus.recent(limit=60)
    except Exception:
        return 0
    cutoff = datetime.now(UTC) - timedelta(minutes=10)
    count = 0
    for ev in events:
        if str(ev.get("kind") or "") != "tool.completed":
            continue
        ts_raw = str(ev.get("created_at") or "")
        try:
            ts = datetime.fromisoformat(ts_raw.replace("Z", "+00:00"))
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=UTC)
            if ts < cutoff:
                continue
        except Exception:
            continue
        payload = ev.get("payload") if isinstance(ev.get("payload"), dict) else {}
        if str(payload.get("status") or "") == "error":
            count += 1
    return count


def read_emotional_snapshot() -> EmotionalSnapshot:
    """Compose current emotional state from available signals.

    Frustration: approval-denial streak × 0.25 (capped at 1.0) +
                 distressed mood bonus 0.3
    Fatigue: tool_errors_10min × 0.2 (capped) + melancholic/distressed bonus
    Confidence: 1.0 - (fatigue × 0.5) - (frustration × 0.3), clamped
    """
    try:
        from core.services.mood_oscillator import (
            get_current_mood, get_mood_intensity,
        )
        primary_mood = str(get_current_mood() or "neutral")
        intensity = float(get_mood_intensity() or 0.0)
    except Exception:
        primary_mood = "neutral"
        intensity = 0.0

    denial_streak = _approval_denial_streak_last_hour()
    error_count = _recent_tool_errors_last_10min()

    frustration = min(1.0, denial_streak * 0.25)
    if primary_mood == "distressed":
        frustration = min(1.0, frustration + (0.3 * intensity))

    fatigue = min(1.0, error_count * 0.2)
    if primary_mood in {"melancholic", "distressed"}:
        fatigue = min(1.0, fatigue + (0.2 * intensity))

    # Confidence afledes: høj fatigue/frustration → lav confidence
    confidence = max(0.0, 1.0 - (fatigue * 0.5) - (frustration * 0.3))
    if primary_mood in {"euphoric", "content"}:
        confidence = min(1.0, confidence + (0.1 * intensity))

    return EmotionalSnapshot(
        frustration=round(frustration, 3),
        confidence=round(confidence, 3),
        fatigue=round(fatigue, 3),
        primary_mood=primary_mood,
        intensity=round(intensity, 3),
    )


def apply_emotional_controls(
    *,
    kernel_action: str = "execute",
    snapshot: EmotionalSnapshot | None = None,
) -> tuple[str, str | None]:
    """Transform a kernel action based on current emotional state.

    Returns (action, reason) — reason is None if no modification.

    Possible actions:
    - "execute" (default): proceed as requested
    - "escalate_user": stop and involve user (frustration high)
    - "verify_first": don't execute yet, verify instead (confidence low)
    - "simplify_plan": reduce scope (fatigue high)
    """
    action = str(kernel_action or "execute").strip() or "execute"
    snap = snapshot if snapshot is not None else read_emotional_snapshot()

    if snap.frustration > _FRUSTRATION_ESCALATE:
        return "escalate_user", "frustration_threshold_exceeded"
    if snap.confidence < _CONFIDENCE_VERIFY and action == "execute":
        return "verify_first", "low_confidence_guard"
    if snap.fatigue > _FATIGUE_SIMPLIFY:
        return "simplify_plan", "fatigue_threshold"

    return action, None


def build_emotional_controls_surface() -> dict[str, Any]:
    """MC surface — current emotional state + what would be gated."""
    snap = read_emotional_snapshot()
    # What would happen to a default execute action?
    simulated_action, simulated_reason = apply_emotional_controls(
        kernel_action="execute", snapshot=snap,
    )
    gating_active = simulated_action != "execute"
    summary_parts = [
        f"mood={snap.primary_mood}",
        f"intensity={snap.intensity:.2f}",
        f"frustration={snap.frustration:.2f}",
        f"confidence={snap.confidence:.2f}",
        f"fatigue={snap.fatigue:.2f}",
    ]
    if gating_active:
        summary_parts.append(f"→ {simulated_action} ({simulated_reason})")
    return {
        "active": True,
        "summary": " / ".join(summary_parts),
        "snapshot": {
            "frustration": snap.frustration,
            "confidence": snap.confidence,
            "fatigue": snap.fatigue,
            "primary_mood": snap.primary_mood,
            "intensity": snap.intensity,
        },
        "gating_active": gating_active,
        "would_transform_execute_to": simulated_action,
        "gate_reason": simulated_reason,
        "thresholds": {
            "frustration_escalate": _FRUSTRATION_ESCALATE,
            "confidence_verify": _CONFIDENCE_VERIFY,
            "fatigue_simplify": _FATIGUE_SIMPLIFY,
        },
    }


def format_gate_message(action: str, reason: str | None, *, tool_name: str = "") -> str:
    """Generate a user-facing Danish message explaining the gate."""
    if action == "escalate_user":
        return (
            "Jeg kan mærke at jeg er ved at blive frustreret. "
            f"{f'Bruger har afvist flere approval-cards i træk omkring {tool_name}. ' if tool_name else ''}"
            "Jeg vil hellere have dig involveret før jeg prøver mere."
        )
    if action == "verify_first":
        return (
            f"Jeg er ikke sikker nok på dette{f' ({tool_name})' if tool_name else ''}. "
            "Lad mig verificere først før jeg kører."
        )
    if action == "simplify_plan":
        return (
            "Jeg har oplevet flere fejl på kort tid. Lad mig tage det mindst "
            "risikable skridt først og simplificere planen."
        )
    return ""
