"""Emotional memory engine.

Captures affective state at runtime anchors (cognitive episodes, perceptual
events, MEMORY.md headings), retrieves similar past anchors via tiered
matching, and surfaces "emotional precedent" cues to the cognitive
conductor.

See docs/superpowers/specs/2026-05-04-emotional-memory-engine-design.md
for the full design.
"""
from __future__ import annotations

import json
import logging
import random
from datetime import UTC, datetime

from core.eventbus.bus import event_bus
from core.runtime.db import insert_emotional_memory_anchor

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Outcome auto-derivation
# ---------------------------------------------------------------------------


def _classify_error(error: str) -> str:
    """Map raw error text to a coarse category for retrieval matching."""
    text = (error or "").lower()
    if not text.strip():
        return "none"
    if "timeout" in text or "timed out" in text:
        return "timeout"
    if "bad request" in text or "http 400" in text:
        return "bad_request"
    if "tool" in text and ("error" in text or "fail" in text):
        return "tool_error"
    return "other"


def _count_tool_errors(error: str, tool_names: list[str]) -> int:
    """Heuristically count how many tools in a run failed.

    Looks for occurrences of "tool <name> ... fail|error" patterns. This is
    intentionally rough — the goal is a 0/1/many bucket for outcome scoring.
    """
    text = (error or "").lower()
    if not text.strip():
        return 0
    count = 0
    for name in tool_names or []:
        nm = str(name or "").lower().strip()
        if not nm:
            continue
        if nm in text and ("error" in text or "fail" in text):
            count += 1
    if count == 0:
        if "fail" in text or "error" in text:
            return 1
    return count


def _derive_outcome_score(
    *, status: str, error: str, tool_error_count: int
) -> tuple[float | None, str | None]:
    """Auto-deriv outcome score from structured episode fields.

    Returns (score, source) where score is in [-1, 1] and source is "auto"
    or None when no determination can be made.
    """
    s = (status or "").strip().lower()
    err = (error or "").lower()
    has_error = bool(err.strip())
    has_strong_error = "timeout" in err or "bad request" in err or "http 400" in err

    if s == "completed" and not has_error and tool_error_count == 0:
        return (0.6, "auto")
    if s == "completed" and (has_error or tool_error_count > 0):
        return (0.0, "auto")
    if s == "interrupted":
        return (-0.4, "auto")
    if has_strong_error or s == "error":
        return (-0.7, "auto")
    if s == "cancelled":
        return (-0.1, "auto")
    return (None, None)


# ---------------------------------------------------------------------------
# Capture flow
# ---------------------------------------------------------------------------


def _read_current_mood() -> tuple[str, float]:
    """Return (mood, intensity). Raises if oscillator is unavailable."""
    from core.services.mood_oscillator import get_current_mood, get_mood_intensity
    return (str(get_current_mood() or ""), float(get_mood_intensity()))


def _read_current_dimensions() -> dict[str, float | None]:
    """Return the 5-dimension live emotional state. May raise — caller handles."""
    from core.services.affective_meta_state import build_affective_meta_state_surface
    surface = build_affective_meta_state_surface()
    live = (surface or {}).get("live_emotional_state") or {}
    return {
        "confidence": _coerce_float_or_none(live.get("confidence")),
        "curiosity": _coerce_float_or_none(live.get("curiosity")),
        "frustration": _coerce_float_or_none(live.get("frustration")),
        "fatigue": _coerce_float_or_none(live.get("fatigue")),
        "trust": _coerce_float_or_none(live.get("trust")),
    }


def _coerce_float_or_none(value: object) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def capture_emotional_anchor(
    *,
    anchor_type: str,
    anchor_id: str,
    context_features: dict[str, object],
    auto_outcome_inputs: dict[str, object] | None = None,
    source: str = "",
    notes: str | None = None,
) -> dict[str, object] | None:
    """Snapshot affect for an anchor and persist it.

    Returns the persisted summary dict, or None on failure (never raises).
    """
    try:
        try:
            mood, intensity = _read_current_mood()
        except Exception as exc:
            logger.debug("emotional_memory: mood read failed: %s", exc)
            return None

        try:
            dims = _read_current_dimensions()
        except Exception as exc:
            logger.debug("emotional_memory: dimension read failed: %s", exc)
            dims = {}

        outcome_score: float | None = None
        outcome_source: str | None = None
        if auto_outcome_inputs:
            try:
                outcome_score, outcome_source = _derive_outcome_score(
                    status=str(auto_outcome_inputs.get("outcome_status") or ""),
                    error=str(auto_outcome_inputs.get("error") or ""),
                    tool_error_count=int(auto_outcome_inputs.get("tool_error_count") or 0),
                )
            except Exception:
                outcome_score, outcome_source = (None, None)

        captured_at = datetime.now(UTC).isoformat()
        try:
            insert_emotional_memory_anchor(
                anchor_type=str(anchor_type),
                anchor_id=str(anchor_id),
                captured_at=captured_at,
                mood=str(mood)[:60],
                intensity=float(intensity),
                confidence=dims.get("confidence"),
                curiosity=dims.get("curiosity"),
                frustration=dims.get("frustration"),
                fatigue=dims.get("fatigue"),
                trust=dims.get("trust"),
                outcome_score=outcome_score,
                outcome_source=outcome_source,
                context_features_json=json.dumps(context_features or {}, ensure_ascii=False)[:4000],
                source=source or None,
                notes=notes,
            )
        except Exception as exc:
            logger.warning("emotional_memory: persist failed: %s", exc)
            return None

        try:
            event_bus.publish(
                "emotional_memory.anchor_captured",
                {
                    "anchor_type": anchor_type,
                    "anchor_id": anchor_id,
                    "mood": mood,
                    "intensity": intensity,
                    "outcome_score": outcome_score,
                },
            )
        except Exception:
            pass

        try:
            if random.random() < 0.01:
                prune_aged_anchors()
        except Exception:
            pass

        return {
            "anchor_type": anchor_type,
            "anchor_id": anchor_id,
            "captured_at": captured_at,
            "mood": mood,
            "intensity": intensity,
            "outcome_score": outcome_score,
            "outcome_source": outcome_source,
        }
    except Exception as exc:
        logger.warning("emotional_memory: capture top-level failure: %s", exc)
        return None


def prune_aged_anchors() -> int:
    """Delete anchors older than the aging threshold unless they are significant.

    Significance criteria (any one keeps the row):
      - intensity >= settings.emotional_memory_significance_intensity
      - outcome_score <= settings.emotional_memory_significance_outcome (clearly bad)

    Returns the number of rows deleted.
    """
    from datetime import timedelta
    from core.runtime.db import connect
    from core.runtime.settings import load_settings

    try:
        settings = load_settings()
        aging_days = int(getattr(settings, "emotional_memory_retention_aging_days", 180))
        sig_intensity = float(getattr(settings, "emotional_memory_significance_intensity", 0.7))
        sig_outcome = float(getattr(settings, "emotional_memory_significance_outcome", -0.3))
    except Exception:
        aging_days, sig_intensity, sig_outcome = (180, 0.7, -0.3)

    cutoff = (datetime.now(UTC) - timedelta(days=aging_days)).isoformat()

    try:
        with connect() as conn:
            cur = conn.execute(
                """
                DELETE FROM emotional_memory_anchors
                WHERE captured_at < ?
                  AND COALESCE(intensity, 0.0) < ?
                  AND (outcome_score IS NULL OR outcome_score > ?)
                """,
                (cutoff, sig_intensity, sig_outcome),
            )
            return int(cur.rowcount or 0)
    except Exception as exc:
        logger.warning("emotional_memory: prune failed: %s", exc)
        return 0


# ---------------------------------------------------------------------------
# Retrieval — tiered similarity matching with aging weight
# ---------------------------------------------------------------------------


_TIER1_THRESHOLD = 0.4
_TIER2_THRESHOLD = 0.25
_TIER1_FETCH_SIZE = 200
_TIER2_FETCH_SIZE = 500


def find_similar_anchors(
    *,
    anchor_type: str,
    context_features: dict[str, object],
    limit: int = 5,
    min_intensity: float = 0.0,
    require_outcome: bool = False,
) -> list[dict[str, object]]:
    """Find similar past anchors. Tiered: structured match first, lexical fallback.

    Returns up to `limit` rows enriched with a `score` field, sorted desc.
    Each row also carries `parsed_context` (decoded context_features_json).
    """
    from core.runtime.db import list_emotional_memory_anchors

    try:
        candidates = list_emotional_memory_anchors(
            anchor_type=anchor_type,
            min_intensity=min_intensity,
            limit=_TIER1_FETCH_SIZE,
        )
    except Exception as exc:
        logger.debug("emotional_memory: candidate fetch failed: %s", exc)
        return []

    parsed = [_with_parsed_context(row) for row in candidates]
    if require_outcome:
        parsed = [r for r in parsed if r.get("outcome_score") is not None]

    tier1 = _tier1_score(anchor_type, context_features, parsed)
    tier1_kept = [r for r in tier1 if r["score"] >= _TIER1_THRESHOLD]

    if len(tier1_kept) >= 2:
        kept = tier1_kept
    else:
        try:
            broad = list_emotional_memory_anchors(
                anchor_type=anchor_type,
                min_intensity=min_intensity,
                limit=_TIER2_FETCH_SIZE,
            )
        except Exception:
            broad = candidates
        broad_parsed = [_with_parsed_context(row) for row in broad]
        if require_outcome:
            broad_parsed = [r for r in broad_parsed if r.get("outcome_score") is not None]
        tier2 = _tier2_lexical_score(context_features, broad_parsed)
        tier2_kept = [r for r in tier2 if r["score"] >= _TIER2_THRESHOLD]
        seen = {r["anchor_id"] for r in tier1_kept}
        kept = list(tier1_kept) + [r for r in tier2_kept if r["anchor_id"] not in seen]

    weighted = [_apply_aging_weight(r) for r in kept]
    weighted = [r for r in weighted if r["score"] > 0.0]
    weighted.sort(key=lambda r: r["score"], reverse=True)
    return weighted[: max(int(limit), 1)]


def _with_parsed_context(row: dict[str, object]) -> dict[str, object]:
    raw = row.get("context_features_json") or "{}"
    try:
        ctx = json.loads(str(raw)) if raw else {}
    except Exception:
        ctx = {}
    return {**row, "parsed_context": ctx}


def _tier1_score(
    anchor_type: str,
    current: dict[str, object],
    candidates: list[dict[str, object]],
) -> list[dict[str, object]]:
    out: list[dict[str, object]] = []
    if anchor_type == "cognitive_episode":
        cur_trigger = str(current.get("trigger") or "")
        cur_tools = set(str(t) for t in (current.get("tool_names") or []))
        cur_status = str(current.get("outcome_status") or "")
        cur_error_kind = str(current.get("error_kind") or "")
        for row in candidates:
            ctx = row.get("parsed_context") or {}
            past_trigger = str(ctx.get("trigger") or "")
            past_tools = set(str(t) for t in (ctx.get("tool_names") or []))
            past_status = str(ctx.get("outcome_status") or "")
            past_error_kind = str(ctx.get("error_kind") or "")
            score = (
                0.5 * (1.0 if cur_trigger and cur_trigger == past_trigger else 0.0)
                + 0.3 * _jaccard(cur_tools, past_tools)
                + 0.1 * (1.0 if cur_status and cur_status == past_status else 0.0)
                + 0.1 * (1.0 if cur_error_kind and cur_error_kind == past_error_kind else 0.0)
            )
            out.append({**row, "score": score, "tier": "structural"})
    elif anchor_type == "perceptual_event":
        cur_kind = str(current.get("event_kind") or "")
        cur_change = str(current.get("change_type") or "")
        for row in candidates:
            ctx = row.get("parsed_context") or {}
            past_kind = str(ctx.get("event_kind") or "")
            past_change = str(ctx.get("change_type") or "")
            score = (
                0.6 * (1.0 if cur_kind and cur_kind == past_kind else 0.0)
                + 0.4 * (1.0 if cur_change and cur_change == past_change else 0.0)
            )
            out.append({**row, "score": score, "tier": "structural"})
    elif anchor_type == "memory_heading":
        cur_heading = str(current.get("heading_display") or "").strip().lower()[:30]
        for row in candidates:
            ctx = row.get("parsed_context") or {}
            past_heading = str(ctx.get("heading_display") or "").strip().lower()[:30]
            score = 1.0 if cur_heading and cur_heading == past_heading else 0.0
            out.append({**row, "score": score, "tier": "structural"})
    else:
        for row in candidates:
            out.append({**row, "score": 0.0, "tier": "structural"})
    return out


def _tier2_lexical_score(
    current: dict[str, object], candidates: list[dict[str, object]]
) -> list[dict[str, object]]:
    cur_summary = str(current.get("summary") or "")
    cur_tokens = _shingle(cur_summary)
    out: list[dict[str, object]] = []
    for row in candidates:
        ctx = row.get("parsed_context") or {}
        past_summary = str(ctx.get("summary") or "")
        past_tokens = _shingle(past_summary)
        score = _jaccard(cur_tokens, past_tokens)
        out.append({**row, "score": score, "tier": "lexical"})
    return out


def _jaccard(a: set[str], b: set[str]) -> float:
    if not a and not b:
        return 0.0
    inter = len(a & b)
    union = len(a | b) or 1
    return inter / union


def _shingle(text: str, *, n: int = 3) -> set[str]:
    """Tokenize lowercased text into overlapping n-grams of words."""
    words = [w for w in (text or "").lower().split() if w]
    if len(words) < n:
        return set(words)
    return {" ".join(words[i : i + n]) for i in range(len(words) - n + 1)}


def _apply_aging_weight(row: dict[str, object]) -> dict[str, object]:
    """Multiply score by aging factor based on captured_at.

    < 30 days  → 1.0
    30-180     → 0.5
    > 180      → 0.0 unless intensity >= 0.7 OR outcome_score <= -0.3
    """
    from core.runtime.settings import load_settings

    try:
        settings = load_settings()
        recent = int(getattr(settings, "emotional_memory_retention_recent_days", 30))
        aging = int(getattr(settings, "emotional_memory_retention_aging_days", 180))
        sig_int = float(getattr(settings, "emotional_memory_significance_intensity", 0.7))
        sig_out = float(getattr(settings, "emotional_memory_significance_outcome", -0.3))
    except Exception:
        recent, aging, sig_int, sig_out = (30, 180, 0.7, -0.3)

    captured_at = str(row.get("captured_at") or "")
    age_days = 0
    try:
        ts = datetime.fromisoformat(captured_at)
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=UTC)
        age_days = (datetime.now(UTC) - ts).days
    except Exception:
        age_days = 0

    score = float(row.get("score") or 0.0)
    if age_days < recent:
        weight = 1.0
    elif age_days <= aging:
        weight = 0.5
    else:
        intensity = float(row.get("intensity") or 0.0)
        outcome = row.get("outcome_score")
        outcome_val = float(outcome) if outcome is not None else 0.0
        if intensity >= sig_int or outcome_val <= sig_out:
            weight = 0.5
        else:
            weight = 0.0

    return {**row, "score": score * weight, "age_days": age_days}


# ---------------------------------------------------------------------------
# Surface for the cognitive conductor
# ---------------------------------------------------------------------------


def build_emotional_memory_surface(
    *,
    anchor_type: str,
    context_features: dict[str, object],
) -> dict[str, object]:
    """Return a bounded surface describing emotional precedent for the current context."""
    from core.runtime.settings import load_settings

    try:
        min_anchors = int(getattr(load_settings(), "emotional_memory_min_anchors", 2))
    except Exception:
        min_anchors = 2

    if not context_features:
        return _inactive_surface()

    try:
        matches = find_similar_anchors(
            anchor_type=anchor_type,
            context_features=context_features,
            limit=8,
        )
    except Exception as exc:
        logger.debug("emotional_memory: surface retrieval failed: %s", exc)
        return _inactive_surface()

    if len(matches) < min_anchors:
        return {
            "active": False,
            "summary": "Insufficient precedent",
            "items": [],
            "match_count": len(matches),
        }

    mood_distribution: dict[str, int] = {}
    intensities: list[float] = []
    outcome_distribution = {"good": 0, "neutral": 0, "bad": 0, "unknown": 0}
    for m in matches:
        mood = str(m.get("mood") or "unknown")
        mood_distribution[mood] = mood_distribution.get(mood, 0) + 1
        try:
            intensities.append(float(m.get("intensity") or 0.0))
        except Exception:
            pass
        outcome = m.get("outcome_score")
        if outcome is None:
            outcome_distribution["unknown"] += 1
        else:
            try:
                v = float(outcome)
                if v <= -0.2:
                    outcome_distribution["bad"] += 1
                elif v >= 0.2:
                    outcome_distribution["good"] += 1
                else:
                    outcome_distribution["neutral"] += 1
            except Exception:
                outcome_distribution["unknown"] += 1

    mean_intensity = (
        round(sum(intensities) / len(intensities), 3) if intensities else 0.0
    )
    directive = _compile_directive(
        match_count=len(matches),
        mood_distribution=mood_distribution,
        outcome_distribution=outcome_distribution,
    )

    items = [
        {
            "anchor_id": m.get("anchor_id"),
            "mood": m.get("mood"),
            "intensity": m.get("intensity"),
            "outcome_score": m.get("outcome_score"),
            "captured_at": m.get("captured_at"),
            "score": round(float(m.get("score") or 0.0), 3),
        }
        for m in matches[:5]
    ]

    return {
        "active": True,
        "anchor_type": anchor_type,
        "match_count": len(matches),
        "mood_distribution": mood_distribution,
        "mean_intensity": mean_intensity,
        "outcome_distribution": outcome_distribution,
        "directive": directive,
        "items": items,
    }


def _inactive_surface() -> dict[str, object]:
    return {
        "active": False,
        "summary": "",
        "items": [],
        "match_count": 0,
    }


def _compile_directive(
    *,
    match_count: int,
    mood_distribution: dict[str, int],
    outcome_distribution: dict[str, int],
) -> str:
    if not match_count:
        return ""
    dominant_mood, dominant_count = max(
        mood_distribution.items(), key=lambda kv: kv[1]
    )
    bad = outcome_distribution.get("bad", 0)
    pieces = [
        f"{match_count} similar contexts:",
        f"mood {dominant_mood} {dominant_count}/{match_count}",
    ]
    if bad >= 1:
        pieces.append(f"outcome bad {bad}/{match_count}")
    if bad >= max(2, match_count // 2):
        pieces.append("recommend pause and synthesis")
    return ", ".join(pieces)


def build_emotional_memory_prompt_section(
    *,
    anchor_type: str,
    context_features: dict[str, object],
) -> str | None:
    """Compact one-line section for inclusion in cognitive_frame_prompt."""
    surface = build_emotional_memory_surface(
        anchor_type=anchor_type, context_features=context_features
    )
    if not surface.get("active"):
        return None
    directive = str(surface.get("directive") or "").strip()
    if not directive:
        return None
    return f"Emotional precedent: {directive[:140]}"
