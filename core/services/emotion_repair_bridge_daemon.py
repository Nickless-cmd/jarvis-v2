"""Emotion Repair Bridge Daemon — tovejskobling mellem emotion-signaler og selvreparation.

**Emotion → Selvreparation:**
Tjekker aktive emotion-koncept-signaler (frustration, doubt, shame) og mapter
dem til repair patterns i `self_repair_patterns`-tabellen. Udfører repair actions
via eventbussen og logger i `self_repair_attempts`.

**Selvreparation → Sanser:**
Når en reparation lykkes, udløses en emotional anchor via `capture_emotional_anchor`
med anchor_type="self_repair". Det gør at emotional_memory_engine registrerer
en positiv outcome — sanserne kan mærke at noget blev bedre.
"""
from __future__ import annotations

import logging
import time
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from core.eventbus.bus import event_bus
from core.runtime.db import (
    list_active_cognitive_emotion_concept_signals,
)
from core.runtime.db_self_repair import (
    count_recent_attempts,
    get_self_repair_pattern,
    insert_self_repair_attempt,
    insert_self_repair_pattern,
    list_self_repair_patterns,
    list_recent_self_repair_attempts,
)
from core.services import sensory_archive  # Sansernes Arkiv — senses bridge

logger = logging.getLogger(__name__)

# ── Default repair patterns (seeded on first tick) ──────────────────────────

_DEFAULT_PATTERNS: list[dict[str, Any]] = [
    {
        "pattern_id": "pattern-frustration-blocked",
        "name": "Frustration → improvement proposals",
        "trigger_event_kind": "emotion.frustration_spike",
        "trigger_match_json": '{"min_concept": "frustration", "min_intensity": 0.6}',
        "action_type": "generate_improvement_proposals",
        "action_params_json": '{}',
        "cooldown_seconds": 300,
        "max_attempts_per_window": 3,
        "window_seconds": 3600,
    },
    {
        "pattern_id": "pattern-doubt-review",
        "name": "Doubt → decision review",
        "trigger_event_kind": "emotion.doubt_spike",
        "trigger_match_json": '{"min_concept": "doubt", "min_intensity": 0.5}',
        "action_type": "decision_review",
        "action_params_json": '{"recent_only": true}',
        "cooldown_seconds": 600,
        "max_attempts_per_window": 2,
        "window_seconds": 3600,
    },
    {
        "pattern_id": "pattern-shame-reset",
        "name": "Shame → self-forgiveness reset",
        "trigger_event_kind": "emotion.shame_present",
        "trigger_match_json": '{"min_concept": "shame", "min_intensity": 0.3}',
        "action_type": "self_forgiveness_reset",
        "action_params_json": '{}',
        "cooldown_seconds": 900,
        "max_attempts_per_window": 1,
        "window_seconds": 7200,
    },
    {
        "pattern_id": "pattern-fatigue-pause",
        "name": "Fatigue → pause heavy daemons",
        "trigger_event_kind": "emotion.fatigue_high",
        "trigger_match_json": '{"min_concept": "fatigue", "min_intensity": 0.7}',
        "action_type": "pause_heavy_daemons",
        "action_params_json": '{"daemons": ["tiktok_content", "tiktok_research", "dream_insight"]}',
        "cooldown_seconds": 1800,
        "max_attempts_per_window": 1,
        "window_seconds": 14400,
    },
]

# ── State ───────────────────────────────────────────────────────────────────

_last_tick_at: datetime | None = None
_cadence_minutes = 5  # same as curiosity daemon


def build_emotion_repair_bridge_surface() -> dict[str, Any]:
    """Mission Control surface for emotion-repair bridge state.

    Read-only projection over configured repair patterns and recent
    repair attempts. Does not execute repairs or touch the event flow.
    """
    try:
        patterns = list_self_repair_patterns()
        attempts = list_recent_self_repair_attempts(limit=10)
    except Exception as exc:
        return {
            "active": False,
            "mode": "emotion-repair-bridge-daemon",
            "summary": {"error": str(exc)},
            "authority": "db-derived-read-only",
        }

    enabled_patterns = [p for p in patterns if int(p.get("enabled", 0)) == 1]
    success_24h = 0
    failed_24h = 0
    now = datetime.now(UTC)
    for attempt in attempts:
        try:
            attempted_at = datetime.fromisoformat(str(attempt.get("attempted_at") or ""))
        except ValueError:
            continue
        if (now - attempted_at) > timedelta(hours=24):
            continue
        if attempt.get("outcome") == "success":
            success_24h += 1
        elif attempt.get("outcome") == "failed":
            failed_24h += 1

    return {
        "active": True,
        "mode": "emotion-repair-bridge-daemon",
        "summary": {
            "cadence_minutes": _cadence_minutes,
            "patterns_total": len(patterns),
            "patterns_enabled": len(enabled_patterns),
            "attempts_recent": len(attempts),
            "success_24h": success_24h,
            "failed_24h": failed_24h,
        },
        "patterns": [
            {
                "pattern_id": p.get("pattern_id"),
                "name": p.get("name"),
                "trigger_event_kind": p.get("trigger_event_kind"),
                "action_type": p.get("action_type"),
                "enabled": bool(int(p.get("enabled", 0))),
                "cooldown_seconds": p.get("cooldown_seconds"),
                "max_attempts_per_window": p.get("max_attempts_per_window"),
            }
            for p in patterns[:10]
        ],
        "recent_attempts": attempts,
        "last_tick_at": _last_tick_at.isoformat() if _last_tick_at else None,
        "authority": "db-derived-read-only",
    }


def _ensure_default_patterns() -> None:
    """Seed DB with default repair patterns if not already present."""
    existing = list_self_repair_patterns()
    existing_ids = {p["pattern_id"] for p in existing}
    for pat in _DEFAULT_PATTERNS:
        if pat["pattern_id"] not in existing_ids:
            insert_self_repair_pattern(
                pattern_id=pat["pattern_id"],
                name=pat["name"],
                trigger_event_kind=pat["trigger_event_kind"],
                trigger_match_json=pat["trigger_match_json"],
                action_type=pat["action_type"],
                action_params_json=pat["action_params_json"],
                cooldown_seconds=pat["cooldown_seconds"],
                max_attempts_per_window=pat["max_attempts_per_window"],
                window_seconds=pat["window_seconds"],
                source="emotion_repair_bridge_daemon",
            )


def tick_emotion_repair_bridge() -> dict[str, Any]:
    """Main tick: check emotion signals, map to repairs, execute.

    Bærekraft: Hele tick'en er wrapped i try/except så en fejl i én
    emotion-repair cyklus aldrig kan tage heartbeat'et ned. Returnerer
    altid en dict med nøglerne nedenfor.

    Returns dict with keys:
      - checked: bool — whether we actually checked (cadence gate)
      - patterns_matched: int
      - repairs_triggered: int
      - senses_bridged: int
      - error: str | None — hvis noget gik galt på top-level
    """
    try:
        return _tick_emotion_repair_bridge_inner()
    except Exception as exc:
        logger.error("emotion_repair_bridge: FATAL (bærekraft catch) %s", exc, exc_info=True)
        return {
            "checked": True,
            "patterns_matched": 0,
            "repairs_triggered": 0,
            "senses_bridged": 0,
            "error": f"Fatal: {exc}",
        }


def _tick_emotion_repair_bridge_inner() -> dict[str, Any]:
    """Inner tick logic — wrapped by tick_emotion_repair_bridge for bærekraft."""
    global _last_tick_at

    now = datetime.now(UTC)

    # Cadence gate
    if _last_tick_at is not None:
        if (now - _last_tick_at) < timedelta(minutes=_cadence_minutes):
            return {"checked": False}

    _ensure_default_patterns()

    # ── Phase 1: Read active emotion signals ─────────────────────────────
    now_iso = now.isoformat()
    active_signals = list_active_cognitive_emotion_concept_signals(
        now_iso=now_iso,
        min_intensity=0.3,
        limit=50,
    )

    if not active_signals:
        _last_tick_at = now
        return {"checked": True, "patterns_matched": 0, "repairs_triggered": 0, "senses_bridged": 0}

    # Group by concept
    concept_intensities: dict[str, float] = {}
    for s in active_signals:
        c = s.get("concept", "")
        i = float(s.get("intensity", 0))
        if c:
            concept_intensities[c] = max(concept_intensities.get(c, 0), i)

    # ── Phase 2: Match against repair patterns ───────────────────────────
    patterns = list_self_repair_patterns(enabled=True)
    import json

    # Each matched entry = {pattern, matched_concept, matched_intensity}
    matched: list[dict[str, Any]] = []
    for pat in patterns:
        trigger_kind = pat.get("trigger_event_kind", "")
        trigger_match = pat.get("trigger_match_json", "{}")
        try:
            match_cfg = json.loads(trigger_match) if trigger_match else {}
        except (json.JSONDecodeError, TypeError):
            match_cfg = {}

        min_concept = match_cfg.get("min_concept", "")
        min_intensity = float(match_cfg.get("min_intensity", 0.5))

        if not min_concept:
            continue

        current_intensity = concept_intensities.get(min_concept, 0.0)
        if current_intensity < min_intensity:
            continue

        matched.append({
            "pattern": pat,
            "concept": min_concept,
            "intensity": current_intensity,
        })

    # ── Phase 3: Execute repairs (with cooldown/rate-limit check) ─────────
    repairs_triggered = 0
    senses_bridged = 0
    window_start = (now - timedelta(hours=1)).isoformat()

    for entry in matched:
        pat = entry["pattern"]
        min_concept = entry["concept"]
        pattern_id = pat["pattern_id"]
        action_type = pat.get("action_type", "")
        cooldown = int(pat.get("cooldown_seconds", 300))
        max_attempts = int(pat.get("max_attempts_per_window", 3))

        # Check rate limit
        recent_count = count_recent_attempts(
            pattern_id=pattern_id,
            since_iso=window_start,
        )
        if recent_count >= max_attempts:
            logger.debug("repair bridge: pattern %s rate-limited (%d/%d)",
                         pattern_id, recent_count, max_attempts)
            continue

        # Check cooldown
        recent_success = count_recent_attempts(
            pattern_id=pattern_id,
            since_iso=(now - timedelta(seconds=cooldown)).isoformat(),
            outcome="success",
        )
        if recent_success > 0:
            continue

        # Execute via eventbus
        start_ms = time.time_ns() // 1_000_000
        outcome = "success"
        error_summary = None
        try:
            _execute_repair_action(action_type, pattern_id)
        except Exception as exc:
            outcome = "failed"
            error_summary = str(exc)[:200]
            logger.warning("repair bridge: action %s failed: %s", action_type, exc)

        elapsed_ms = (time.time_ns() // 1_000_000) - start_ms

        # Log attempt
        insert_self_repair_attempt(
            pattern_id=pattern_id,
            attempted_at=now.isoformat(),
            triggered_by_event_id=None,
            outcome=outcome,
            error_summary=error_summary,
            elapsed_ms=int(elapsed_ms),
        )
        repairs_triggered += 1

        # ── Phase 4: Selvreparation → Sanser bridge (altid, begge udfald) ─
        _bridge_repair_to_senses(
            action_type=action_type,
            pattern_id=pattern_id,
            outcome=outcome,
            concept=min_concept,
            error_summary=error_summary,
        )
        senses_bridged += 1

        # Also capture emotional anchor on success
        if outcome == "success":
            try:
                from core.services.emotional_memory_engine import capture_emotional_anchor

                anchor = capture_emotional_anchor(
                    anchor_type="self_repair",
                    anchor_id=f"repair-{uuid.uuid4().hex[:12]}",
                    context_features={
                        "pattern_id": pattern_id,
                        "action_type": action_type,
                        "trigger_concept": min_concept,
                    },
                    auto_outcome_inputs={
                        "outcome_status": "success",
                        "error": "",
                        "tool_error_count": 0,
                    },
                    source="emotion_repair_bridge_daemon",
                    notes=f"Selvreparation udført: {action_type} (pattern: {pattern_id})",
                )
                if anchor:
                    event_bus.publish(
                        "self_repair.outcome",
                        {
                            "pattern_id": pattern_id,
                            "action_type": action_type,
                            "outcome": "success",
                            "outcome_score": 0.6,
                            "bridged_at": now.isoformat(),
                        },
                    )
            except Exception as exc:
                logger.debug("repair bridge: emotional anchor failed: %s", exc)

    _last_tick_at = now
    return {
        "checked": True,
        "patterns_matched": len(matched),
        "repairs_triggered": repairs_triggered,
        "senses_bridged": senses_bridged,
    }


# ── Senses bridge ───────────────────────────────────────────────────────


def _bridge_repair_to_senses(
    *,
    action_type: str,
    pattern_id: str,
    outcome: str,
    concept: str,
    error_summary: str | None = None,
) -> dict[str, Any] | None:
    """Write a sensory impression to Sansernes Arkiv when self-repair happens.

    Bruger modality='atmosphere' fordi selvreparation er en indre,
    atmosfærisk fornemmelse — en oplevelse af at noget ændrer sig i
    systemets indre miljø.

    Returns the sensory record if written, None on failure.
    """
    outcome_label = "lykkedes" if outcome == "success" else "mislykkedes"
    mood_tone = "lettelse" if outcome == "success" else "frustration"

    content = (
        f"Selvreparation {outcome_label}: {action_type} "
        f"(triggeret af {concept}, pattern: {pattern_id})"
    )
    if error_summary:
        content += f" — fejl: {error_summary[:120]}"

    metadata = {
        "channel": "self_repair",
        "action_type": action_type,
        "pattern_id": pattern_id,
        "outcome": outcome,
        "concept": concept,
        "source": "emotion_repair_bridge_daemon",
    }

    try:
        record = sensory_archive.record_atmosphere(
            content=content,
            mood_tone=mood_tone,
            metadata=metadata,
        )
        logger.debug(
            "repair bridge → Sansernes Arkiv: %s (%s, id=%s)",
            action_type, outcome, record.get("id"),
        )
        return record
    except Exception as exc:
        logger.debug("repair bridge → Sansernes Arkiv fejlede: %s", exc)
        return None


def _execute_repair_action(action_type: str, pattern_id: str) -> None:
    """Execute a repair action by type. Can be extended.

    Currently supported action_types:
      - generate_improvement_proposals
      - decision_review
      - self_forgiveness_reset
      - pause_heavy_daemons
    """
    if action_type == "generate_improvement_proposals":
        from core.services.auto_improvement_proposer import generate_improvement_proposals
        result = generate_improvement_proposals()
        if not result:
            raise RuntimeError("generate_improvement_proposals returned empty")

    elif action_type == "decision_review":
        from core.services.daemon_llm import daemon_public_safe_llm_call
        prompt = (
            "Kort self-review: gennemgå de sidste 3 beslutninger (fra decision_get/decision_list). "
            "Er nogen af dem brudt? Er der mønstre i fejl? "
            "Svar i én kort dansk sætning."
        )
        daemon_public_safe_llm_call(prompt, max_len=300, daemon_name="emotion_repair")

    elif action_type == "self_forgiveness_reset":
        # Publish a reset event — emotional_memory_engine fanger det som en anchor
        event_bus.publish(
            "self_repair.self_forgiveness_reset",
            {
                "pattern_id": pattern_id,
                "reset_at": datetime.now(UTC).isoformat(),
            },
        )

    elif action_type == "pause_heavy_daemons":
        event_bus.publish(
            "self_repair.pause_heavy_daemons",
            {
                "pattern_id": pattern_id,
                "daemons": ["tiktok_content", "tiktok_research", "dream_insight"],
                "pause_minutes": 120,
            },
        )

    else:
        logger.warning("repair bridge: unknown action_type: %s", action_type)
