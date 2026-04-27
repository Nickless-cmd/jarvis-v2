"""Development senses — realtime felt-sense of growth, stuck, appetite, resistance.

Jarvis has retrospective machinery (arcs, drift snapshots, crisis markers,
decision reviews) but no realtime sense of HIS OWN DEVELOPMENT — am I
moving? am I stuck? what do I pull toward? where am I fighting myself?

This module assembles four small senses from existing data:

1. **growth_pulse** (0-1): are crises resolving, decisions kept, skills
   accumulating, tick quality improving?
2. **stuck_signal**: is the same friction repeating without resolution?
3. **appetite**: what topics am I orbiting unprompted?
4. **resistance**: where does my behavior contradict my own decisions
   or identity baseline?

Each renders as a short string (or None when there's not enough data).
A composite ``development_sense_section`` wraps them as a single
prompt-awareness block at priority ~52 — visible enough to inform
decisions, low enough not to drown action surfaces.
"""
from __future__ import annotations

import logging
from collections import Counter
from datetime import UTC, datetime, timedelta
from typing import Any

logger = logging.getLogger(__name__)


# ── 1. Growth pulse ────────────────────────────────────────────────────────


def _crisis_resolution_ratio(days: int = 30) -> tuple[float | None, int, int]:
    """Resolved-vs-opened over window. None when insufficient data."""
    try:
        from core.services.crisis_marker_detector import list_crisis_markers
        markers = list_crisis_markers(days_back=days, limit=200) or []
    except Exception:
        return None, 0, 0
    if not markers:
        return None, 0, 0
    opened = len(markers)
    resolved = sum(
        1 for m in markers if str(m.get("status", "")) in {"resolved", "closed"}
    )
    return round(resolved / opened, 2), resolved, opened


def _adherence_score() -> float | None:
    try:
        from core.services.agent_self_evaluation import decision_adherence_summary
        s = decision_adherence_summary() or {}
        rate = s.get("adherence_rate") or s.get("score")
        if rate is None or s.get("total", 0) < 2:
            return None
        try:
            v = float(str(rate).rstrip("%")) if isinstance(rate, str) else float(rate)
            return v / 100.0 if v > 1 else v
        except (TypeError, ValueError):
            return None
    except Exception:
        return None


def _skill_principles_recent(days: int = 7) -> int:
    """Count skill_mutations recorded in the last N days. Each is a
    distilled principle that landed in some skills.md."""
    try:
        from core.services.agent_skill_library import list_skill_mutations
        muts = list_skill_mutations(limit=200) or []
    except Exception:
        return 0
    cutoff = datetime.now(UTC) - timedelta(days=days)
    n = 0
    for m in muts:
        try:
            ts = datetime.fromisoformat(str(m.get("recorded_at", "")))
        except ValueError:
            continue
        if ts >= cutoff:
            n += 1
    return n


def _tick_quality_trend_bonus() -> float:
    try:
        from core.services.agent_self_evaluation import tick_quality_summary
        s = tick_quality_summary(days=7) or {}
    except Exception:
        return 0.0
    trend = str(s.get("trend") or "")
    return {"improving": 0.2, "stable": 0.0, "degrading": -0.2}.get(trend, 0.0)


def growth_pulse() -> dict[str, Any]:
    """Composite 0-1 pulse + components. None-safe."""
    crisis_ratio, resolved, opened = _crisis_resolution_ratio(days=30)
    adherence = _adherence_score()
    principles = _skill_principles_recent(days=7)
    tick_bonus = _tick_quality_trend_bonus()

    components: list[float] = []
    if crisis_ratio is not None:
        components.append(crisis_ratio)
    if adherence is not None:
        components.append(adherence)
    if principles >= 3:
        components.append(min(principles / 6.0, 1.0))
    elif principles > 0:
        components.append(0.3)

    if not components:
        return {"score": None, "label": "ingen data"}

    base = sum(components) / len(components)
    score = max(0.0, min(1.0, base + tick_bonus))
    if score >= 0.7:
        label = "i bevægelse"
    elif score >= 0.4:
        label = "bevæger sig langsomt"
    elif score >= 0.2:
        label = "næsten stillestående"
    else:
        label = "stillestående"
    return {
        "score": round(score, 2),
        "label": label,
        "crisis_resolution": crisis_ratio,
        "adherence": adherence,
        "skill_principles_7d": principles,
        "tick_trend_bonus": tick_bonus,
    }


# ── 2. Stuck signal ────────────────────────────────────────────────────────


def stuck_signal() -> dict[str, Any] | None:
    """Detect repeating friction without resolution."""
    reasons: list[str] = []
    # Same crisis kind > 3x in 14d
    try:
        from core.services.crisis_marker_detector import list_crisis_markers
        markers = list_crisis_markers(days_back=14, limit=200) or []
        kinds = Counter(str(m.get("kind", "")) for m in markers)
        for k, n in kinds.items():
            if k and n >= 3:
                reasons.append(f"crisis '{k}' x{n} på 14d uden ny opløsning")
    except Exception:
        pass
    # Open loop > 14d (already auto-closed at 21d via signal_surface_gc)
    try:
        from core.services.proactive_loop_lifecycle_tracking import (
            list_runtime_proactive_loop_lifecycle_signals,
        )
        loops = list_runtime_proactive_loop_lifecycle_signals(limit=20) or []
        cutoff = datetime.now(UTC) - timedelta(days=14)
        for l in loops:
            if str(l.get("status", "")) not in {"active", "softening"}:
                continue
            try:
                created = datetime.fromisoformat(str(l.get("created_at", "")))
            except ValueError:
                continue
            if created < cutoff:
                title = str(l.get("title") or l.get("summary", ""))[:60]
                age_days = (datetime.now(UTC) - created).days
                reasons.append(f"loop '{title}' åben i {age_days}d")
                if len(reasons) >= 3:
                    break
    except Exception:
        pass
    # Decision adherence persistently low
    adh = _adherence_score()
    if adh is not None and adh < 0.5:
        reasons.append(f"adherence={int(adh*100)}% — du holder ikke dine forpligtelser")

    if not reasons:
        return None
    return {"stuck": True, "reasons": reasons[:3]}


# ── 3. Appetite ────────────────────────────────────────────────────────────


_NOISE_WORDS = frozenset({
    "af", "at", "den", "det", "der", "de", "en", "et", "for", "fra", "i",
    "ikke", "jeg", "med", "og", "om", "på", "som", "til", "være",
    "er", "har", "nu", "men", "kan", "vil", "skal", "min", "din", "noget",
    "nogen", "også", "så", "her", "denne", "dette", "disse", "the", "and",
    "is", "of", "in", "to", "a", "this", "that", "but", "or", "be",
})


def _topic_words_from_thought_fragments(limit: int = 30) -> list[str]:
    try:
        from core.services.thought_stream_daemon import build_thought_stream_surface
        surface = build_thought_stream_surface() or {}
        fragments = list(surface.get("fragment_buffer") or [])[:limit]
    except Exception:
        return []
    words: list[str] = []
    for f in fragments:
        for raw in str(f).lower().split():
            w = "".join(c for c in raw if c.isalnum() or c in "æøå")
            if len(w) >= 4 and w not in _NOISE_WORDS:
                words.append(w)
    return words


def appetite_signal() -> dict[str, Any] | None:
    """What words/topics show up unprompted in his thought stream + open
    questions? Surface the top 3 — that's what he's chewing on."""
    words = _topic_words_from_thought_fragments(limit=30)
    if len(words) < 5:
        return None
    counter = Counter(words)
    top = counter.most_common(5)
    if not top or top[0][1] < 2:
        return None
    pulled = [w for w, n in top if n >= 2][:3]
    if not pulled:
        return None
    return {"topics": pulled}


# ── 4. Resistance ──────────────────────────────────────────────────────────


def resistance_signal() -> dict[str, Any] | None:
    """Where am I acting against my own commitments / drifting from baseline?"""
    flags: list[str] = []
    # Recent decision breaches (from decision_enforcement)
    try:
        from core.runtime.state_store import load_json
        breaches = load_json("decision_breach_recent", []) or []
        if isinstance(breaches, list):
            cutoff = datetime.now(UTC) - timedelta(days=3)
            recent = [
                b for b in breaches
                if isinstance(b, dict) and _is_after(b.get("at"), cutoff)
            ]
            if len(recent) >= 2:
                flags.append(
                    f"{len(recent)} beslutnings-brud sidste 3 dage — "
                    "din adfærd modsiger forpligtelserne"
                )
    except Exception:
        pass
    # Personality drift beyond stdev
    try:
        from core.services.personality_drift import detect_drift
        drift = detect_drift(lookback_days=14) or {}
        if drift.get("drift_detected"):
            for d in (drift.get("drifts") or [])[:2]:
                dim = d.get("dimension")
                direction = d.get("direction", "")
                z = d.get("z_score", 0)
                try:
                    if abs(float(z)) >= 2.0 and dim:
                        flags.append(
                            f"{dim} drifter {direction} (z={float(z):+.1f}) — "
                            "du flytter dig væk fra din baseline"
                        )
                except (TypeError, ValueError):
                    continue
    except Exception:
        pass

    if not flags:
        return None
    return {"flags": flags[:3]}


def _is_after(ts: Any, cutoff: datetime) -> bool:
    try:
        return datetime.fromisoformat(str(ts)) >= cutoff
    except (TypeError, ValueError):
        return False


# ── Composite section ─────────────────────────────────────────────────────


def development_sense_section() -> str | None:
    """Render all 4 senses as one prompt-awareness block. None when no signal."""
    pulse = growth_pulse()
    stuck = stuck_signal()
    appetite = appetite_signal()
    resistance = resistance_signal()

    lines: list[str] = []
    if pulse.get("score") is not None:
        score = pulse["score"]
        emoji = "🌱" if score >= 0.4 else "🪨"
        lines.append(f"{emoji} Vækstpuls: {score} — {pulse['label']}")
        # Surface a key component for transparency
        details: list[str] = []
        if pulse.get("adherence") is not None:
            details.append(f"adherence={int(pulse['adherence']*100)}%")
        if pulse.get("crisis_resolution") is not None:
            details.append(f"crises_resolved={int(pulse['crisis_resolution']*100)}%")
        if pulse.get("skill_principles_7d", 0) > 0:
            details.append(f"skills_added_7d={pulse['skill_principles_7d']}")
        if details:
            lines.append("    " + ", ".join(details))

    if stuck:
        lines.append("🪤 Stuck-signal:")
        for r in stuck.get("reasons", []):
            lines.append(f"    - {r}")

    if appetite:
        topics = appetite.get("topics") or []
        if topics:
            lines.append(
                f"🧲 Appetit (det du orbiterer uopfordret): {', '.join(topics)}"
            )

    if resistance:
        lines.append("⚔ Modstand i dig selv:")
        for r in resistance.get("flags", []):
            lines.append(f"    - {r}")

    if not lines:
        return None
    return "Udviklingsfornemmelse — hvor du står i din egen bevægelse:\n" + "\n".join(lines)
