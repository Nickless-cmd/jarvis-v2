from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

from core.eventbus.bus import event_bus
from core.runtime.db import (
    list_runtime_world_model_signals,
    supersede_runtime_world_model_signals,
    update_runtime_world_model_signal_status,
    upsert_runtime_world_model_signal,
)
from core.runtime.settings import load_settings
from core.runtime.state_store import load_json, save_json
from core.services.chat_sessions import get_chat_session, list_chat_sessions

import re as _re

# Pattern phrases for nudge detection (Phase 1 of world model loop).
# Each pattern matches in Jarvis' OWN response text.
_PREDICTION_PHRASES = [
    _re.compile(r"\bjeg tror\b", _re.IGNORECASE),
    _re.compile(r"\bjeg vil tro\b", _re.IGNORECASE),
    _re.compile(r"\bforventer (at|en|et|den|de)\b", _re.IGNORECASE),
    _re.compile(r"\bgætter på\b", _re.IGNORECASE),
    _re.compile(r"\bdet vil (sandsynligvis|nok|måske)\b", _re.IGNORECASE),
    _re.compile(r"\bdet bliver (nok|sandsynligvis)\b", _re.IGNORECASE),
    _re.compile(r"\bdet skal nok\b", _re.IGNORECASE),
    _re.compile(r"\bsandsynligvis\b", _re.IGNORECASE),
    _re.compile(r"\bjeg satser på\b", _re.IGNORECASE),
]

_RESOLUTION_PHRASES = [
    _re.compile(r"\bdet viste sig\b", _re.IGNORECASE),
    _re.compile(r"\bjeg fik ret\b", _re.IGNORECASE),
    _re.compile(r"\bjeg tog fejl\b", _re.IGNORECASE),
    _re.compile(r"\bsom forventet\b", _re.IGNORECASE),
    _re.compile(r"\boverrasket over\b", _re.IGNORECASE),
    _re.compile(r"\bblev som\b", _re.IGNORECASE),
    _re.compile(r"\bvirkede (ikke|som forventet)\b", _re.IGNORECASE),
    _re.compile(r"\bdet gik (ikke )?som\b", _re.IGNORECASE),
]

_NUDGE_STATE_KEY = "runtime_world_model_nudges"
_MAX_NUDGES_PER_KIND = 20
_NUDGE_TTL_HOURS = 48  # Jarvis review: 24h was too short for overnight gap
_NUDGE_CONTEXT_WORDS = 30

_CONFIDENCE_RANKS = {"low": 1, "medium": 2, "high": 3}
_SOURCE_KIND_RANKS = {
    "runtime-derived-support": 1,
    "session-evidence": 2,
    "repeated-session-evidence": 3,
    "user-explicit": 4,
}
_STALE_AFTER_DAYS = 10
_PREDICTION_STATE_KEY = "runtime_world_model_predictions"
_MAX_PREDICTIONS = 120
_PREDICTION_ALLOWED_EFFECTS = [
    "prompt_attention",
    "compare_future_observations",
    "update_calibration_only",
    "do_not_auto_act",
]


def record_runtime_world_model_prediction(
    *,
    subject: str,
    expectation: str,
    horizon: str = "",
    confidence: str = "low",
    evidence: list[str] | None = None,
    source: str = "runtime",
    now: datetime | None = None,
) -> dict[str, object]:
    """Record an explicit, falsifiable world-model expectation.

    This is deliberately a small ledger, not a planner. A prediction may
    influence attention and later calibration, but it must not execute work.
    """
    normalized_subject = " ".join(str(subject or "").split()).strip()
    normalized_expectation = " ".join(str(expectation or "").split()).strip()
    if not normalized_subject:
        return {"status": "error", "error": "subject is required"}
    if not normalized_expectation:
        return {"status": "error", "error": "expectation is required"}

    created_at = (now or datetime.now(UTC)).isoformat()
    confidence = str(confidence or "low").strip().lower()
    if confidence not in _CONFIDENCE_RANKS:
        confidence = "low"
    item = {
        "prediction_id": f"worldpred-{uuid4().hex}",
        "status": "open",
        "subject": normalized_subject,
        "expectation": normalized_expectation,
        "horizon": " ".join(str(horizon or "").split()).strip(),
        "confidence": confidence,
        "evidence": [str(e).strip() for e in (evidence or []) if str(e).strip()][:5],
        "source": str(source or "runtime").strip() or "runtime",
        "created_at": created_at,
        "updated_at": created_at,
        "resolved_at": "",
        "observed": "",
        "outcome": "",
        "allowed_effects": list(_PREDICTION_ALLOWED_EFFECTS),
    }
    predictions = _load_predictions()
    predictions.insert(0, item)
    _save_predictions(predictions[:_MAX_PREDICTIONS])
    try:
        event_bus.publish(
            "world_model_signal.prediction_recorded",
            {
                "prediction_id": item["prediction_id"],
                "subject": item["subject"],
                "confidence": item["confidence"],
            },
        )
    except Exception:
        pass  # never block recording on event-bus errors
    return {"status": "ok", "prediction": item}


def resolve_runtime_world_model_prediction(
    prediction_id: str,
    *,
    observed: str,
    outcome: str,
    now: datetime | None = None,
    resolved_via: str = "tool",
) -> dict[str, object]:
    """Resolve a prediction with a later observation."""
    normalized_id = str(prediction_id or "").strip()
    normalized_observed = " ".join(str(observed or "").split()).strip()
    normalized_outcome = str(outcome or "").strip().lower()
    if normalized_outcome not in {"supported", "contradicted", "uncertain"}:
        return {
            "status": "error",
            "error": "outcome must be supported, contradicted, or uncertain",
        }
    predictions = _load_predictions()
    resolved_at = (now or datetime.now(UTC)).isoformat()
    for item in predictions:
        if str(item.get("prediction_id") or "") != normalized_id:
            continue
        item["status"] = "resolved"
        item["observed"] = normalized_observed
        item["outcome"] = normalized_outcome
        item["resolved_at"] = resolved_at
        item["updated_at"] = resolved_at
        item["resolved_via"] = str(resolved_via or "tool")
        _save_predictions(predictions)
        try:
            event_bus.publish(
                "world_model_signal.prediction_resolved",
                {
                    "prediction_id": normalized_id,
                    "outcome": normalized_outcome,
                },
            )
        except Exception:
            pass  # never block resolution on event-bus errors
        return {"status": "ok", "prediction": item}
    return {"status": "error", "error": f"prediction '{normalized_id}' not found"}


def build_runtime_world_model_prediction_surface(*, limit: int = 6) -> dict[str, object]:
    predictions = _load_predictions()
    open_items = [p for p in predictions if str(p.get("status") or "") == "open"]
    resolved_items = [
        p for p in predictions
        if str(p.get("status") or "") == "resolved"
    ]
    supported = [
        p for p in resolved_items
        if str(p.get("outcome") or "") == "supported"
    ]
    contradicted = [
        p for p in resolved_items
        if str(p.get("outcome") or "") == "contradicted"
    ]
    scored_total = len(supported) + len(contradicted)
    calibration = round(len(supported) / scored_total, 2) if scored_total else None
    ordered = [*open_items, *resolved_items][: max(limit, 1)]
    return {
        "active": bool(open_items),
        "items": ordered,
        "summary": {
            "open_count": len(open_items),
            "resolved_count": len(resolved_items),
            "supported_count": len(supported),
            "contradicted_count": len(contradicted),
            "calibration": calibration,
            "current_prediction": str(
                (open_items[0] if open_items else {}).get("expectation")
                or "No open world-model prediction"
            ),
        },
        "allowed_effects": list(_PREDICTION_ALLOWED_EFFECTS),
    }


def track_runtime_world_model_signals_for_visible_turn(
    *,
    session_id: str | None,
    run_id: str,
    user_message: str,
) -> dict[str, object]:
    normalized_session_id = str(session_id or "").strip()
    normalized_message = " ".join(str(user_message or "").split()).strip()
    if not normalized_message and not normalized_session_id:
        return {
            "created": 0,
            "updated": 0,
            "corrected": 0,
            "items": [],
            "summary": "No world-model evidence was available.",
        }

    corrected = _apply_correction_signals(user_message=normalized_message)
    signals = _extract_world_model_candidates(
        user_message=normalized_message,
        session_id=normalized_session_id,
    )
    items = _persist_world_model_signals(
        signals=signals,
        session_id=normalized_session_id,
        run_id=run_id,
    )
    return {
        "created": len([item for item in items if item.get("was_created")]),
        "updated": len([item for item in items if item.get("was_updated")]),
        "corrected": corrected,
        "items": items,
        "summary": (
            f"Tracked {len(items)} bounded world-model signals and corrected {corrected}."
            if items or corrected
            else "No bounded world-model assumption warranted tracking."
        ),
    }


def refresh_runtime_world_model_signal_statuses() -> dict[str, int]:
    now = datetime.now(UTC)
    refreshed = 0
    for item in list_runtime_world_model_signals(limit=40):
        if str(item.get("status") or "") not in {"active", "uncertain"}:
            continue
        updated_at = _parse_dt(str(item.get("updated_at") or item.get("created_at") or ""))
        if updated_at is None or updated_at > now - timedelta(days=_STALE_AFTER_DAYS):
            continue
        refreshed_item = update_runtime_world_model_signal_status(
            str(item.get("signal_id") or ""),
            status="stale",
            updated_at=now.isoformat(),
            status_reason="Marked stale after bounded inactivity window.",
        )
        if refreshed_item is not None:
            refreshed += 1
            event_bus.publish(
                "world_model_signal.stale",
                {
                    "signal_id": refreshed_item.get("signal_id"),
                    "signal_type": refreshed_item.get("signal_type"),
                    "status": refreshed_item.get("status"),
                    "summary": refreshed_item.get("summary"),
                },
            )
    return {"stale_marked": refreshed}


def build_runtime_world_model_signal_surface(*, limit: int = 8) -> dict[str, object]:
    refresh_runtime_world_model_signal_statuses()
    items = list_runtime_world_model_signals(limit=max(limit, 1))
    active = [item for item in items if str(item.get("status") or "") == "active"]
    uncertain = [item for item in items if str(item.get("status") or "") == "uncertain"]
    corrected = [item for item in items if str(item.get("status") or "") == "corrected"]
    stale = [item for item in items if str(item.get("status") or "") == "stale"]
    superseded = [item for item in items if str(item.get("status") or "") == "superseded"]
    ordered_items = [*active, *uncertain, *corrected, *stale, *superseded]
    latest = next(iter(active or uncertain or corrected or stale or superseded), None)
    return {
        "active": bool(active),
        "items": ordered_items,
        "summary": {
            "active_count": len(active),
            "uncertain_count": len(uncertain),
            "corrected_count": len(corrected),
            "stale_count": len(stale),
            "superseded_count": len(superseded),
            "current_signal": str((latest or {}).get("title") or "No active world-model signal"),
            "current_status": str((latest or {}).get("status") or "none"),
        },
        "prediction_skeleton": build_runtime_world_model_prediction_surface(),
    }


def _extract_pattern_matches(text: str, patterns: list) -> list[dict[str, str]]:
    """Return list of {matched_phrase, context_excerpt} for each regex hit.

    Context excerpt = ~30 words before and after the match.
    """
    if not text:
        return []
    words = text.split()
    matches: list[dict[str, str]] = []
    for pat in patterns:
        for m in pat.finditer(text):
            char_pos = m.start()
            running_chars = 0
            word_idx = 0
            for i, w in enumerate(words):
                if running_chars + len(w) >= char_pos:
                    word_idx = i
                    break
                running_chars += len(w) + 1
            start = max(0, word_idx - _NUDGE_CONTEXT_WORDS)
            end = min(len(words), word_idx + _NUDGE_CONTEXT_WORDS)
            context_excerpt = " ".join(words[start:end])
            matches.append({
                "matched_phrase": m.group(0),
                "context_excerpt": context_excerpt[:400],
            })
    return matches


def extract_prediction_language(text: str) -> list[dict[str, str]]:
    """Find prediction-shape phrases in Jarvis' own response text."""
    return _extract_pattern_matches(text, _PREDICTION_PHRASES)


def extract_resolution_language(text: str) -> list[dict[str, str]]:
    """Find resolution-shape phrases in Jarvis' own response text."""
    return _extract_pattern_matches(text, _RESOLUTION_PHRASES)


def _loop_enabled() -> bool:
    """World-model-loop kill-switch check."""
    try:
        return bool(load_settings().world_model_loop_enabled)
    except Exception:
        return True


def _load_nudges() -> dict[str, list[dict[str, object]]]:
    raw = load_json(_NUDGE_STATE_KEY, {})
    if not isinstance(raw, dict):
        raw = {}
    return {
        "prediction_nudges": list(raw.get("prediction_nudges") or []),
        "resolution_nudges": list(raw.get("resolution_nudges") or []),
    }


def _save_nudges(data: dict[str, list[dict[str, object]]]) -> None:
    save_json(_NUDGE_STATE_KEY, data)


def record_prediction_nudge(
    *,
    session_id: str,
    run_id: str,
    matched_phrase: str,
    context_excerpt: str,
) -> None:
    """Append a prediction-language nudge to state (FIFO, max 20, 48h TTL)."""
    now = datetime.now(UTC)
    nudge = {
        "nudge_id": f"wmnudge-{uuid4().hex}",
        "kind": "prediction",
        "session_id": str(session_id or ""),
        "run_id": str(run_id or ""),
        "matched_phrase": str(matched_phrase or "")[:80],
        "context_excerpt": str(context_excerpt or "")[:400],
        "created_at": now.isoformat(),
        "rendered_at": "",
        "expires_at": (now + timedelta(hours=_NUDGE_TTL_HOURS)).isoformat(),
    }
    data = _load_nudges()
    data["prediction_nudges"].append(nudge)
    if len(data["prediction_nudges"]) > _MAX_NUDGES_PER_KIND:
        data["prediction_nudges"] = data["prediction_nudges"][-_MAX_NUDGES_PER_KIND:]
    _save_nudges(data)


def record_resolution_nudge(
    *,
    session_id: str,
    run_id: str,
    matched_phrase: str,
    context_excerpt: str,
    candidate_prediction_id: str = "",
) -> None:
    """Append a resolution-language nudge to state (FIFO, max 20, 48h TTL)."""
    now = datetime.now(UTC)
    nudge = {
        "nudge_id": f"wmnudge-{uuid4().hex}",
        "kind": "resolution",
        "session_id": str(session_id or ""),
        "run_id": str(run_id or ""),
        "matched_phrase": str(matched_phrase or "")[:80],
        "context_excerpt": str(context_excerpt or "")[:400],
        "candidate_prediction_id": str(candidate_prediction_id or ""),
        "created_at": now.isoformat(),
        "rendered_at": "",
        "expires_at": (now + timedelta(hours=_NUDGE_TTL_HOURS)).isoformat(),
    }
    data = _load_nudges()
    data["resolution_nudges"].append(nudge)
    if len(data["resolution_nudges"]) > _MAX_NUDGES_PER_KIND:
        data["resolution_nudges"] = data["resolution_nudges"][-_MAX_NUDGES_PER_KIND:]
    _save_nudges(data)


_HORIZON_DEFAULT_GRACE_DAYS = 7
_TTL_GRACE_HOURS = 24


def _next_weekday(d: datetime, target_weekday: int) -> datetime:
    """Next occurrence of given weekday (0=Mon..6=Sun) at end-of-day."""
    days_ahead = (target_weekday - d.weekday()) % 7
    if days_ahead == 0:
        days_ahead = 7
    return (d + timedelta(days=days_ahead)).replace(hour=23, minute=59)


def _parse_horizon(horizon: str, created: datetime) -> datetime:
    """Return the cutoff datetime when horizon would have elapsed.

    Conservative: only matches known phrases (case-insensitive). Anything
    else falls back to a 7-day default grace.
    """
    h = (horizon or "").strip().lower()
    if h:
        if h.startswith("i dag") or h == "eod":
            return created.replace(hour=23, minute=59)
        if h.startswith("i morgen"):
            return (created + timedelta(days=1)).replace(hour=23, minute=59)
        if h.startswith("denne uge"):
            return created + timedelta(days=7)
        weekday_map = {
            "mandag": 0, "tirsdag": 1, "onsdag": 2, "torsdag": 3,
            "fredag": 4, "lørdag": 5, "søndag": 6,
        }
        for name, idx in weekday_map.items():
            if h.startswith(f"inden {name}"):
                return _next_weekday(created, idx)
    return created + timedelta(days=_HORIZON_DEFAULT_GRACE_DAYS)


def _ttl_sweep_open_predictions(*, now: datetime | None = None) -> dict[str, int]:
    """Scan open predictions; auto-resolve as 'uncertain' if past horizon+grace.

    Returns {"resolved": N, "skipped": M}. Honors killswitch.
    """
    if not _loop_enabled():
        return {"resolved": 0, "skipped": 0, "reason": "killswitch_off"}

    cutoff_now = now or datetime.now(UTC)
    predictions = _load_predictions()
    resolved = 0
    skipped = 0
    for pred in predictions:
        if str(pred.get("status") or "") != "open":
            skipped += 1
            continue
        try:
            created = datetime.fromisoformat(
                str(pred.get("created_at") or "").replace("Z", "+00:00")
            )
        except Exception:
            skipped += 1
            continue
        horizon_cutoff = _parse_horizon(str(pred.get("horizon") or ""), created)
        if cutoff_now < horizon_cutoff + timedelta(hours=_TTL_GRACE_HOURS):
            skipped += 1
            continue
        resolve_runtime_world_model_prediction(
            str(pred.get("prediction_id") or ""),
            observed="(no observation — TTL auto-resolve)",
            outcome="uncertain",
            now=cutoff_now,
            resolved_via="ttl_auto",
        )
        resolved += 1
    return {"resolved": resolved, "skipped": skipped}


def format_world_model_nudges_for_awareness(*, session_id: str | None = None) -> str:
    """Surface up to 1 prediction-nudge + 1 resolution-nudge for the awareness block.

    Picks oldest unrendered+unexpired nudge per kind. Marks them as rendered.
    Returns empty string if killswitch off or nothing to surface.
    """
    if not _loop_enabled():
        return ""
    now = datetime.now(UTC)
    data = _load_nudges()
    parts: list[str] = []
    dirty = False

    for kind in ("prediction_nudges", "resolution_nudges"):
        for n in data.get(kind, []):
            if n.get("rendered_at"):
                continue
            try:
                exp = datetime.fromisoformat(str(n.get("expires_at") or "").replace("Z", "+00:00"))
            except Exception:
                continue
            if exp <= now:
                continue
            phrase = str(n.get("matched_phrase") or "")
            if kind == "prediction_nudges":
                parts.append(
                    f"📡 Du sagde '{phrase}' — vil du lave en prediction? "
                    "Brug predict_outcome hvis ja."
                )
            else:
                cand = str(n.get("candidate_prediction_id") or "")
                hint = f" (kandidat: {cand[:16]})" if cand else ""
                parts.append(
                    f"🎯 Du sagde '{phrase}' — vil du resolve en prediction{hint}? "
                    "Brug resolve_prediction hvis ja."
                )
            n["rendered_at"] = now.isoformat()
            dirty = True
            break  # only one per kind per session

    if dirty:
        _save_nudges(data)
    return "\n".join(parts)


_MILESTONE_STATE_KEY = "runtime_world_model_milestones"


def _load_milestones() -> dict[str, list[dict[str, object]]]:
    raw = load_json(_MILESTONE_STATE_KEY, {})
    if not isinstance(raw, dict):
        raw = {}
    return {"history": list(raw.get("history") or [])}


def _save_milestones(data: dict[str, list[dict[str, object]]]) -> None:
    save_json(_MILESTONE_STATE_KEY, data)


def _resolved_predictions_chrono() -> list[dict[str, object]]:
    """Return resolved predictions in chronological order (oldest first)."""
    preds = _load_predictions()
    resolved = [
        p for p in preds
        if str(p.get("status") or "") == "resolved"
        and str(p.get("outcome") or "") in {"supported", "contradicted", "uncertain"}
    ]
    resolved.sort(key=lambda p: str(p.get("resolved_at") or p.get("created_at") or ""))
    return resolved


def _calibration_of(predictions: list[dict[str, object]]) -> float:
    """% supported among supported+contradicted; uncertain is excluded."""
    s = sum(1 for p in predictions if p.get("outcome") == "supported")
    c = sum(1 for p in predictions if p.get("outcome") == "contradicted")
    if s + c == 0:
        return 0.0
    return round(100.0 * s / (s + c), 1)


def _has_milestone(kind: str, value: object = None) -> bool:
    """Check if a milestone of given kind (+ optional value) has been recorded."""
    for m in _load_milestones().get("history", []):
        if m.get("kind") != kind:
            continue
        if value is not None and m.get("value") != value:
            continue
        return True
    return False


def _append_milestone(kind: str, value: object, message: str, now: datetime) -> dict[str, object]:
    m = {
        "milestone_id": f"wmmile-{uuid4().hex}",
        "kind": kind,
        "value": value,
        "message": message,
        "created_at": now.isoformat(),
        "rendered_at": "",
    }
    data = _load_milestones()
    data["history"].append(m)
    _save_milestones(data)
    return m


def _compute_calibration_milestone(*, now: datetime | None = None) -> dict[str, object] | None:
    """Compute the latest calibration milestone if any rule fires.

    Rules in priority order:
      1. count_10 — every 10th resolved prediction (10, 20, 30 ...)
      2. first_contradiction_after_streak — latest is contradicted after ≥5 supported
      3. threshold_60 / threshold_70 / threshold_80 — calibration crossed since last
      4. trend_improving (≥+5%) / trend_declining (≤-5%) — last 10 vs prior 10
    Returns the newly recorded milestone dict, or None if nothing fires.
    """
    if not _loop_enabled():
        return None

    now = now or datetime.now(UTC)
    resolved = _resolved_predictions_chrono()
    count = len(resolved)
    if count == 0:
        return None

    calibration = _calibration_of(resolved[-30:])

    # Rule 1: count_10
    if count > 0 and count % 10 == 0 and not _has_milestone("count_10", count):
        message = f"Du har nu {count} resolved predictions. Kalibrering sidste 30: {calibration}%."
        return _append_milestone("count_10", count, message, now)

    # Rule 2: first_contradiction_after_streak
    if count >= 6 and resolved[-1].get("outcome") == "contradicted":
        prior_5 = resolved[-6:-1]
        if all(p.get("outcome") == "supported" for p in prior_5):
            pid = str(resolved[-1].get("prediction_id") or "")
            if not _has_milestone("first_contradiction_after_streak", pid):
                message = (
                    f"Du tog fejl efter {len(prior_5)} rigtige predictions i træk. "
                    "Worth noting."
                )
                return _append_milestone(
                    "first_contradiction_after_streak", pid, message, now,
                )

    # Rule 3: threshold cross
    for tier in (60, 70, 80):
        kind = f"threshold_{tier}"
        if calibration >= tier and not _has_milestone(kind):
            message = f"Din kalibrering er nu {calibration}% — over {tier}%."
            return _append_milestone(kind, tier, message, now)

    # Rule 4: trend (Jarvis-addition)
    if count >= 20:
        recent_10 = resolved[-10:]
        prior_10 = resolved[-20:-10]
        recent_cal = _calibration_of(recent_10)
        prior_cal = _calibration_of(prior_10)
        delta = round(recent_cal - prior_cal, 1)
        if delta >= 5:
            anchor = f"improving:{count}"
            if not _has_milestone("trend_improving", anchor):
                message = (
                    f"Din kalibrering er steget {delta}% over de sidste 10 predictions. "
                    "Du bliver bedre."
                )
                return _append_milestone("trend_improving", anchor, message, now)
        elif delta <= -5:
            anchor = f"declining:{count}"
            if not _has_milestone("trend_declining", anchor):
                message = (
                    f"Din kalibrering er faldet {abs(delta)}%. Hvad har ændret sig?"
                )
                return _append_milestone("trend_declining", anchor, message, now)

    return None


def format_world_model_milestone_for_awareness() -> str:
    """Surface one unrendered milestone per call. Returns '' when nothing."""
    if not _loop_enabled():
        return ""
    _compute_calibration_milestone()

    data = _load_milestones()
    for m in data.get("history", []):
        if m.get("rendered_at"):
            continue
        m["rendered_at"] = datetime.now(UTC).isoformat()
        _save_milestones(data)
        return f"🧮 {m.get('message')}"
    return ""


def _load_predictions() -> list[dict[str, object]]:
    raw = load_json(_PREDICTION_STATE_KEY, [])
    if not isinstance(raw, list):
        return []
    return [item for item in raw if isinstance(item, dict)]


def _save_predictions(predictions: list[dict[str, object]]) -> None:
    save_json(_PREDICTION_STATE_KEY, predictions[:_MAX_PREDICTIONS])


def _extract_world_model_candidates(*, user_message: str, session_id: str) -> list[dict[str, object]]:
    signals: list[dict[str, object]] = []

    project_context = _project_context_signal(user_message, session_id=session_id)
    if project_context:
        signals.append(project_context)

    workspace_scope = _workspace_scope_signal(user_message)
    if workspace_scope:
        signals.append(workspace_scope)

    deduped: dict[str, dict[str, object]] = {}
    for item in signals:
        key = str(item.get("canonical_key") or "")
        if not key:
            continue
        current = deduped.get(key)
        if current is None:
            deduped[key] = item
            continue
        current_rank = _rank(_CONFIDENCE_RANKS, str(current.get("confidence") or ""))
        next_rank = _rank(_CONFIDENCE_RANKS, str(item.get("confidence") or ""))
        if next_rank >= current_rank:
            deduped[key] = item
    return list(deduped.values())


def _project_context_signal(message: str, *, session_id: str) -> dict[str, object] | None:
    text = (message or "").strip()
    lower = text.lower()
    if not any(marker in lower for marker in ("bygger jarvis", "building jarvis", "jarvis together")):
        return None
    history = _recent_user_message_history(limit_sessions=6, per_session_limit=4)
    support_count = 0
    matching_sessions: set[str] = set()
    for item in history:
        if _matches_project_context(str(item.get("content") or "")):
            support_count += 1
            if item.get("session_id"):
                matching_sessions.add(str(item["session_id"]))
    if session_id:
        matching_sessions.add(session_id)
    status = "active" if support_count >= 2 else "uncertain"
    confidence = "high" if support_count >= 2 and len(matching_sessions) > 1 else "medium"
    source_kind = "repeated-session-evidence" if support_count >= 2 else "session-evidence"
    return {
        "signal_type": "project-context-assumption",
        "canonical_key": "world-model:project-context:building-jarvis-together",
        "status": status,
        "title": "Current project context: building Jarvis together",
        "summary": "Jarvis is carrying a bounded assumption that the current work is building Jarvis together.",
        "rationale": "Repeated visible project-context cues suggest this is part of Jarvis' active situational understanding.",
        "source_kind": source_kind,
        "confidence": confidence,
        "evidence_summary": _quote(text),
        "support_summary": f"{support_count} matching project-context cues across {max(len(matching_sessions), 1)} session(s).",
        "support_count": max(support_count, 1),
        "session_count": max(len(matching_sessions), 1),
        "status_reason": "Repeated project-context cues keep this assumption active." if status == "active" else "Single-session project-context cue kept as uncertain situational understanding.",
    }


def _workspace_scope_signal(message: str) -> dict[str, object] | None:
    text = (message or "").strip()
    lower = text.lower()
    if not any(marker in lower for marker in ("inside jarvis-v2", "inside jarvis v2", "kun i jarvis-v2", "work only inside jarvis-v2")):
        return None
    return {
        "signal_type": "workspace-scope-assumption",
        "canonical_key": "world-model:workspace-scope:jarvis-v2",
        "status": "active",
        "title": "Current workspace scope: jarvis-v2",
        "summary": "Jarvis is carrying a bounded assumption that the active workspace scope is jarvis-v2.",
        "rationale": "Explicit workspace-scope instruction is a situational assumption Jarvis should carry visibly while it remains relevant.",
        "source_kind": "user-explicit",
        "confidence": "high",
        "evidence_summary": _quote(text),
        "support_summary": "Explicit workspace-scope instruction from visible user message.",
        "support_count": 1,
        "session_count": 1,
        "status_reason": "Explicit situational scope instruction is active.",
    }


def _persist_world_model_signals(
    *,
    signals: list[dict[str, object]],
    session_id: str,
    run_id: str,
) -> list[dict[str, object]]:
    now = datetime.now(UTC).isoformat()
    persisted: list[dict[str, object]] = []
    for signal in signals:
        persisted_item = upsert_runtime_world_model_signal(
            signal_id=f"worldmodel-{uuid4().hex}",
            signal_type=str(signal.get("signal_type") or "world-model-signal"),
            canonical_key=str(signal.get("canonical_key") or ""),
            status=str(signal.get("status") or "uncertain"),
            title=str(signal.get("title") or ""),
            summary=str(signal.get("summary") or ""),
            rationale=str(signal.get("rationale") or ""),
            source_kind=str(signal.get("source_kind") or ""),
            confidence=str(signal.get("confidence") or "low"),
            evidence_summary=str(signal.get("evidence_summary") or ""),
            support_summary=str(signal.get("support_summary") or ""),
            support_count=int(signal.get("support_count") or 1),
            session_count=int(signal.get("session_count") or 1),
            created_at=now,
            updated_at=now,
            status_reason=str(signal.get("status_reason") or ""),
            run_id=run_id,
            session_id=session_id,
        )
        if persisted_item.get("was_created"):
            # New signal created - supersede older signals of same type if this is higher confidence
            signal_type = str(persisted_item.get("signal_type") or "")
            confidence = str(persisted_item.get("confidence") or "low")
            if signal_type and confidence in ("high", "medium"):
                superseded_count = supersede_runtime_world_model_signals(
                    signal_type=signal_type,
                    exclude_signal_id=str(persisted_item.get("signal_id") or ""),
                    updated_at=now,
                    status_reason="Superseded by newer bounded assumption with higher confidence.",
                )
                if superseded_count > 0:
                    event_bus.publish(
                        "world_model_signal.superseded",
                        {
                            "signal_id": persisted_item.get("signal_id"),
                            "signal_type": signal_type,
                            "superseded_count": superseded_count,
                            "summary": f"Superseded {superseded_count} older signal(s) of same type.",
                        },
                    )
            event_bus.publish(
                "world_model_signal.created",
                {
                    "signal_id": persisted_item.get("signal_id"),
                    "signal_type": persisted_item.get("signal_type"),
                    "status": persisted_item.get("status"),
                    "summary": persisted_item.get("summary"),
                },
            )
        elif persisted_item.get("was_updated"):
            event_bus.publish(
                "world_model_signal.updated",
                {
                    "signal_id": persisted_item.get("signal_id"),
                    "signal_type": persisted_item.get("signal_type"),
                    "status": persisted_item.get("status"),
                    "summary": persisted_item.get("summary"),
                },
            )
        persisted.append(persisted_item)
    return persisted


def _apply_correction_signals(*, user_message: str) -> int:
    lower = str(user_message or "").lower()
    corrected = 0
    corrections = [
        (
            "world-model:project-context:building-jarvis-together",
            any(marker in lower for marker in ("bygger ikke jarvis", "not building jarvis", "ikke jarvis sammen længere", "not jarvis together anymore")),
        ),
        (
            "world-model:workspace-scope:jarvis-v2",
            any(marker in lower for marker in ("ikke kun i jarvis-v2", "not inside jarvis-v2", "not only inside jarvis-v2", "ikke i jarvis-v2 længere")),
        ),
    ]
    now = datetime.now(UTC).isoformat()
    active_items = list_runtime_world_model_signals(limit=20)
    for canonical_key, should_correct in corrections:
        if not should_correct:
            continue
        for item in active_items:
            if str(item.get("canonical_key") or "") != canonical_key:
                continue
            if str(item.get("status") or "") not in {"active", "uncertain"}:
                continue
            updated = update_runtime_world_model_signal_status(
                str(item.get("signal_id") or ""),
                status="corrected",
                updated_at=now,
                status_reason="User explicitly corrected this situational assumption.",
            )
            if updated is None:
                continue
            corrected += 1
            event_bus.publish(
                "world_model_signal.corrected",
                {
                    "signal_id": updated.get("signal_id"),
                    "signal_type": updated.get("signal_type"),
                    "status": updated.get("status"),
                    "summary": updated.get("summary"),
                },
            )
    return corrected


def _recent_user_message_history(*, limit_sessions: int, per_session_limit: int) -> list[dict[str, object]]:
    items: list[dict[str, object]] = []
    for session in list_chat_sessions()[: max(limit_sessions, 1)]:
        session_id = str(session.get("id") or "")
        if not session_id:
            continue
        detail = get_chat_session(session_id)
        if not detail:
            continue
        user_messages = [
            {
                "session_id": session_id,
                "content": " ".join(str(message.get("content") or "").split()).strip(),
            }
            for message in reversed(detail.get("messages") or [])
            if str(message.get("role") or "") == "user"
        ]
        items.extend(user_messages[: max(per_session_limit, 1)])
    return items


def _matches_project_context(message: str) -> bool:
    lower = str(message or "").lower()
    return any(marker in lower for marker in ("bygger jarvis", "building jarvis", "jarvis together"))


def _parse_dt(value: str) -> datetime | None:
    try:
        return datetime.fromisoformat(str(value or "").replace("Z", "+00:00"))
    except ValueError:
        return None


def _rank(ranks: dict[str, int], value: str) -> int:
    return int(ranks.get(str(value or "").strip().lower(), 0))


def _quote(text: str) -> str:
    normalized = " ".join(str(text or "").split()).strip()
    if len(normalized) > 180:
        normalized = normalized[:179].rstrip() + "…"
    return f'"{normalized}"' if normalized else ""
