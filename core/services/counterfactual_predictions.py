"""Counterfactual → world-model prediction binding.

Closes the prediction-resolution loop Jarvis flagged in his 7-day
Counterfactuals Phase 1 review (2026-05-14): 1019 counterfactuals
generated, 0 predictions, 0 resolutions.

The architectural intent of counterfactuals is calibration over time —
"if X had been different, Y would have happened" is unfalsifiable as
written, but the *underlying claim about regret patterns* IS observable:
"this trigger_type will recur less often if we apply the learning".

This module:

1. ``bind_counterfactual_to_prediction(cf_id, trigger_type, anchor,
   confidence)`` — call when a new counterfactual is created. Records a
   world-model prediction with:
     - subject:     f"future {trigger_type} events"
     - expectation: f"declining frequency vs prior {HORIZON_DAYS} days
                     after learning from {cf_id}"
     - horizon:     "{HORIZON_DAYS} days"
     - source:      "counterfactual"
     - evidence:    [f"counterfactual:{cf_id}", anchor[:80]]
   The cf_id is encoded in evidence so we can locate a counterfactual's
   prediction without a schema migration.

2. ``sweep_expired_counterfactual_predictions()`` — periodic sweep that
   resolves predictions whose horizon has expired. V1 marks them as
   "uncertain" with a structured note. Future Phase 2 will compare
   trigger_type frequency in the post-horizon window against the
   pre-horizon baseline to assign supported/contradicted.

3. ``list_open_counterfactual_predictions()`` — read-only view so MC
   and Jarvis-the-LLM can inspect what's pending.

Killswitch: respects ``RuntimeSettings.counterfactual_engine_enabled``
— if the engine is disabled, binding is a no-op so the predictions
ledger doesn't fill up with orphaned entries.
"""
from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from typing import Any

logger = logging.getLogger(__name__)

# How far into the future we project. Counterfactual triggers are
# typically about session/day-level decisions, so a week is a natural
# horizon: long enough to see if patterns recur, short enough to keep
# the ledger fresh.
HORIZON_DAYS = 7

# Grace period after horizon expires before auto-resolving.
# Lets a manual resolution-tool catch it first if Jarvis wants to.
GRACE_DAYS = 1

# Frequency-comparison thresholds for Phase 2 supported/contradicted
# verdicts. The counterfactual claims the learning will reduce future
# events of the same trigger kind, so:
#   post < baseline * (1 - DELTA) → supported (declined)
#   post > baseline * (1 + DELTA) → contradicted (increased)
#   else                          → uncertain (roughly stable)
# A baseline below MIN_BASELINE_COUNT is too noisy to judge → uncertain.
FREQ_DELTA = 0.30
MIN_BASELINE_COUNT = 3


def _confidence_band(numeric: float) -> str:
    """Map a 0..1 confidence to the world-model band strings."""
    if numeric >= 0.7:
        return "high"
    if numeric >= 0.4:
        return "medium"
    return "low"


def bind_counterfactual_to_prediction(
    *,
    cf_id: str,
    trigger_type: str,
    anchor: str = "",
    confidence: float = 0.5,
    source: str = "counterfactual",
    event_kind: str = "",
) -> dict[str, Any]:
    """Record a world-model prediction linked to a counterfactual.

    ``event_kind`` is the concrete eventbus kind that triggered the
    counterfactual (e.g. "conflict.detected", "self_review_outcome.created").
    When provided, it's embedded in the prediction's evidence list so the
    Phase 2 sweep can compare frequency in the baseline vs. post-horizon
    windows. For abstract legacy trigger_types ("decision", "correction",
    ...) callers may pass the actual event_kind they classified from.

    Best-effort: never raises. Returns the prediction dict on success,
    or {"status": "skipped", "reason": ...} on no-op paths.
    """
    cf_id = str(cf_id or "").strip()
    trigger_type = str(trigger_type or "").strip() or "unknown"
    if not cf_id:
        return {"status": "skipped", "reason": "empty cf_id"}

    # Respect the engine killswitch — if counterfactuals are off,
    # don't fill the predictions ledger with orphans.
    try:
        from core.runtime.settings import RuntimeSettings
        if not RuntimeSettings().counterfactual_engine_enabled:
            return {"status": "skipped", "reason": "engine-killswitch-off"}
    except Exception:
        pass  # settings unavailable — proceed best-effort

    try:
        from core.services.world_model_signal_tracking import (
            record_runtime_world_model_prediction,
        )
    except Exception as exc:
        logger.debug("counterfactual_predictions: world_model import failed: %s", exc)
        return {"status": "error", "reason": f"world-model-unavailable: {exc}"}

    subject = f"future {trigger_type} events"
    expectation = (
        f"declining frequency vs prior {HORIZON_DAYS} days "
        f"after learning encoded in counterfactual {cf_id}"
    )
    band = _confidence_band(float(confidence or 0.0))
    # Evidence carries structured back-pointers so the sweep can find
    # what to count without a schema migration:
    #   - "counterfactual:<cf_id>" — links back to the source row
    #   - "event_kind:<kind>" — the event_kind to count in baseline/post windows
    #   - anchor — free-form context (truncated)
    evidence = [f"counterfactual:{cf_id}"]
    if event_kind:
        evidence.append(f"event_kind:{event_kind}")
    if anchor:
        evidence.append(str(anchor)[:80])

    try:
        result = record_runtime_world_model_prediction(
            subject=subject,
            expectation=expectation,
            horizon=f"{HORIZON_DAYS} days",
            confidence=band,
            evidence=evidence,
            source=source,
        )
    except Exception as exc:
        logger.debug("counterfactual_predictions: record failed: %s", exc)
        return {"status": "error", "reason": f"record-failed: {exc}"}

    if isinstance(result, dict) and result.get("status") == "ok":
        return result
    return {"status": "error", "reason": "record-returned-non-ok", "raw": result}


def list_open_counterfactual_predictions() -> list[dict[str, Any]]:
    """Return all open predictions whose source=='counterfactual'."""
    try:
        from core.services.world_model_signal_tracking import _load_predictions  # type: ignore
    except Exception:
        return []
    out: list[dict[str, Any]] = []
    for item in _load_predictions():
        if not isinstance(item, dict):
            continue
        if str(item.get("status") or "") != "open":
            continue
        if str(item.get("source") or "") != "counterfactual":
            continue
        out.append(item)
    return out


def _is_horizon_expired(prediction: dict[str, Any], now: datetime) -> bool:
    """Check if a prediction's horizon has passed (with grace period)."""
    try:
        created = datetime.fromisoformat(str(prediction.get("created_at") or ""))
    except ValueError:
        return False
    elapsed = now - created
    return elapsed.total_seconds() >= (HORIZON_DAYS + GRACE_DAYS) * 86400


def _extract_event_kind(prediction: dict[str, Any]) -> str:
    """Pull the event_kind tag out of a prediction's evidence list."""
    for ev in prediction.get("evidence") or []:
        ev = str(ev)
        if ev.startswith("event_kind:"):
            return ev[len("event_kind:") :].strip()
    return ""


def _frequency_verdict(
    *, event_kind: str, created_at: datetime
) -> dict[str, Any]:
    """Compare event_kind frequency before vs after the prediction's birth.

    Counts events of ``event_kind`` in [created-H, created] (baseline) and
    [created, created+H] (post), where H = HORIZON_DAYS. Returns a dict:
        {outcome: "supported"|"contradicted"|"uncertain",
         baseline: int, post: int, ratio: float, reason: str}
    """
    if not event_kind:
        return {
            "outcome": "uncertain",
            "baseline": 0,
            "post": 0,
            "ratio": 0.0,
            "reason": "no-event-kind-tag-on-prediction",
        }
    try:
        from core.runtime.db import connect
    except Exception as exc:
        return {
            "outcome": "uncertain", "baseline": 0, "post": 0, "ratio": 0.0,
            "reason": f"db-import-failed: {exc}",
        }

    window = timedelta(days=HORIZON_DAYS)
    baseline_start = (created_at - window).isoformat()
    midpoint = created_at.isoformat()
    post_end = (created_at + window).isoformat()

    try:
        with connect() as conn:
            row = conn.execute(
                "SELECT COUNT(*) FROM events WHERE kind = ? "
                "AND created_at >= ? AND created_at < ?",
                (event_kind, baseline_start, midpoint),
            ).fetchone()
            baseline = int(row[0]) if row else 0
            row = conn.execute(
                "SELECT COUNT(*) FROM events WHERE kind = ? "
                "AND created_at >= ? AND created_at < ?",
                (event_kind, midpoint, post_end),
            ).fetchone()
            post = int(row[0]) if row else 0
    except Exception as exc:
        return {
            "outcome": "uncertain", "baseline": 0, "post": 0, "ratio": 0.0,
            "reason": f"query-failed: {exc}",
        }

    if baseline < MIN_BASELINE_COUNT:
        return {
            "outcome": "uncertain", "baseline": baseline, "post": post,
            "ratio": 0.0,
            "reason": f"baseline-too-noisy ({baseline} < {MIN_BASELINE_COUNT})",
        }
    ratio = post / baseline if baseline > 0 else 0.0
    if ratio < (1.0 - FREQ_DELTA):
        outcome = "supported"
        reason = f"declined {int((1-ratio)*100)}% vs baseline"
    elif ratio > (1.0 + FREQ_DELTA):
        outcome = "contradicted"
        reason = f"increased {int((ratio-1)*100)}% vs baseline"
    else:
        outcome = "uncertain"
        reason = f"stable ({int(ratio*100)}% of baseline, within ±{int(FREQ_DELTA*100)}%)"
    return {
        "outcome": outcome, "baseline": baseline, "post": post,
        "ratio": round(ratio, 3), "reason": reason,
    }


def sweep_expired_counterfactual_predictions(
    *, now: datetime | None = None
) -> dict[str, Any]:
    """Auto-resolve counterfactual predictions whose horizon has expired.

    Phase 2 (2026-05-14): trigger-frequency comparison.

    For each expired open prediction tagged with an event_kind, count
    eventbus rows of that kind in the baseline window (created-H..created)
    and the post window (created..created+H). Resolve as:
      - supported   when frequency declined by >= FREQ_DELTA
      - contradicted when frequency increased by >= FREQ_DELTA
      - uncertain   when within ±FREQ_DELTA, or baseline too noisy,
                    or evidence lacks an event_kind tag

    Returns a summary dict — never raises.
    """
    started = (now or datetime.now(UTC))
    summary: dict[str, Any] = {
        "started_at": started.isoformat(),
        "open_count": 0,
        "expired_count": 0,
        "resolved_count": 0,
        "by_outcome": {"supported": 0, "contradicted": 0, "uncertain": 0},
        "errors": 0,
    }
    try:
        from core.services.world_model_signal_tracking import (
            resolve_runtime_world_model_prediction,
        )
    except Exception as exc:
        summary["errors"] += 1
        summary["error_detail"] = f"world-model-import: {exc}"
        return summary

    open_predictions = list_open_counterfactual_predictions()
    summary["open_count"] = len(open_predictions)
    for pred in open_predictions:
        if not _is_horizon_expired(pred, started):
            continue
        summary["expired_count"] += 1
        prediction_id = str(pred.get("prediction_id") or "")
        if not prediction_id:
            continue

        # Extract event_kind from evidence and run the frequency
        # comparison. Falls back to "uncertain" with explanatory reason
        # if event_kind is missing (legacy predictions from before the
        # Phase 2 binding update will lack the tag).
        event_kind = _extract_event_kind(pred)
        try:
            created_at = datetime.fromisoformat(str(pred.get("created_at") or ""))
        except ValueError:
            created_at = started - timedelta(days=HORIZON_DAYS + GRACE_DAYS)

        verdict = _frequency_verdict(event_kind=event_kind, created_at=created_at)
        outcome = verdict["outcome"]
        observed_text = (
            f"frequency comparison ({event_kind or 'unknown-kind'}): "
            f"baseline={verdict['baseline']} post={verdict['post']} "
            f"ratio={verdict['ratio']} — {verdict['reason']}"
        )

        try:
            res = resolve_runtime_world_model_prediction(
                prediction_id,
                observed=observed_text,
                outcome=outcome,
                resolved_via="counterfactual-sweep-phase2",
            )
        except Exception as exc:
            logger.debug("counterfactual_predictions: resolve failed for %s: %s",
                         prediction_id, exc)
            summary["errors"] += 1
            continue
        if isinstance(res, dict) and res.get("status") == "ok":
            summary["resolved_count"] += 1
            summary["by_outcome"][outcome] = summary["by_outcome"].get(outcome, 0) + 1
        else:
            summary["errors"] += 1

    try:
        from core.eventbus.bus import event_bus
        event_bus.publish("counterfactual_predictions.sweep_complete", dict(summary))
    except Exception:
        pass
    return summary


def build_counterfactual_predictions_surface() -> dict[str, object]:
    """Mission Control surface — read-only meta-projection."""
    open_preds = list_open_counterfactual_predictions()
    return {
        "active": True,
        "mode": "counterfactual_predictions",
        "summary": (
            f"{len(open_preds)} open counterfactual-bound predictions "
            f"(horizon={HORIZON_DAYS}d, grace={GRACE_DAYS}d)"
        ),
        "open_count": len(open_preds),
        "authority": "derived-read-only",
    }


def _emit_counterfactual_predictions_event(
    kind: str, payload: dict[str, object] | None = None
) -> None:
    """Defensive scoped event emitter."""
    try:
        from core.eventbus.bus import event_bus
        event_bus.publish(f"counterfactual_predictions.{kind}", payload or {})
    except Exception:
        pass
