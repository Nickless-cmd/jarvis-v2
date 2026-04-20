"""Prompt Mutation Loop — score applied mutations, recommend rollback if bad.

Ported concept from jarvis-ai (2026-03), adapted safely for v2.

The old version auto-applied prompt changes and rolled back on score < -0.10.
That's delicate — prompt files like SOUL.md and IDENTITY.md must never be
auto-mutated. v2's prompt_evolution_runtime.py produces proposals; this
module is the *closed loop* piece: when a proposal is applied (approved or
otherwise), register it here, and the loop will score subsequent signals
and *recommend* rollback when the score drops.

This service does NOT write to prompt files. It observes + recommends.
Actual file mutation and rollback remain the user's/Jarvis' choice — via
existing proposal flows or explicit tool calls.

Scoring window: 24h after application. Signal inputs:
+ declining error rate, stable-or-rising mood, user agreement ratio
- rising error rate, mood drop, pushback ratio rising
"""
from __future__ import annotations

import json
import logging
import os
import statistics
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)

_STORAGE_REL = "workspaces/default/runtime/prompt_mutations.json"
_SCORING_WINDOW_HOURS = 24
_ROLLBACK_SCORE_THRESHOLD = -0.10
_ADOPTION_SCORE_THRESHOLD = 0.20
_ADOPTION_AGE_HOURS = 48  # after this age + good score, mark adopted
_MAX_RECORDS = 500


def _storage_path() -> Path:
    base = os.environ.get("JARVIS_HOME") or os.path.expanduser("~/.jarvis-v2")
    return Path(base) / _STORAGE_REL


def _load() -> list[dict[str, Any]]:
    path = _storage_path()
    if not path.exists():
        return []
    try:
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):
            return data
    except Exception as exc:
        logger.warning("prompt_mutation_loop: load failed: %s", exc)
    return []


def _save(items: list[dict[str, Any]]) -> None:
    path = _storage_path()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".tmp")
        with tmp.open("w", encoding="utf-8") as f:
            json.dump(items, f, ensure_ascii=False, indent=2)
        tmp.replace(path)
    except Exception as exc:
        logger.warning("prompt_mutation_loop: save failed: %s", exc)


def _snapshot_signals() -> dict[str, float]:
    """Capture current state of signals used for mutation scoring."""
    snap: dict[str, float] = {}
    try:
        from core.services.mood_oscillator import _combined_value  # type: ignore
        snap["mood"] = float(_combined_value())
    except Exception:
        pass
    try:
        from core.runtime.db import recent_heartbeat_outcome_counts  # type: ignore
        counts = recent_heartbeat_outcome_counts(minutes=60) or {}
        total = sum(int(v) for v in counts.values()) or 1
        errors = int(counts.get("error", 0)) + int(counts.get("blocked", 0))
        snap["error_rate"] = round(errors / total, 3)
    except Exception:
        pass
    try:
        from core.services.conflict_memory import recent_pushback_ratio  # type: ignore
        snap["pushback_rate"] = float(recent_pushback_ratio())
    except Exception:
        pass
    try:
        from core.services.valence_trajectory import get_trajectory
        traj = get_trajectory() or {}
        if "score" in traj:
            snap["valence"] = float(traj["score"])
    except Exception:
        pass
    return snap


def record_mutation(
    *,
    target_file: str,
    source: str = "prompt_evolution",
    reason: str = "",
    metadata: dict[str, Any] | None = None,
) -> str:
    """Register an applied prompt mutation. Takes baseline signal snapshot."""
    items = _load()
    mutation_id = f"pmut-{uuid4().hex[:12]}"
    items.append({
        "mutation_id": mutation_id,
        "target_file": str(target_file)[:160],
        "source": str(source)[:80],
        "reason": str(reason)[:300],
        "metadata": dict(metadata or {}),
        "applied_at": datetime.now(UTC).isoformat(),
        "baseline_signals": _snapshot_signals(),
        "status": "monitoring",
        "score": None,
        "score_updated_at": None,
        "recommendation": None,
        "closed_at": None,
    })
    if len(items) > _MAX_RECORDS:
        items = items[-_MAX_RECORDS:]
    _save(items)
    return mutation_id


def _score_mutation(item: dict[str, Any]) -> dict[str, Any]:
    """Compute current score delta vs baseline.

    score > 0: current signals better than baseline
    score < 0: current signals worse than baseline
    """
    baseline = item.get("baseline_signals") or {}
    current = _snapshot_signals()
    contributions: list[float] = []

    # mood: higher is better
    if "mood" in baseline and "mood" in current:
        delta = float(current["mood"]) - float(baseline["mood"])
        contributions.append(delta * 0.3)

    # error_rate: lower is better → negate delta
    if "error_rate" in baseline and "error_rate" in current:
        delta = float(current["error_rate"]) - float(baseline["error_rate"])
        contributions.append(-delta * 0.4)

    # pushback_rate: lower is better → negate delta
    if "pushback_rate" in baseline and "pushback_rate" in current:
        delta = float(current["pushback_rate"]) - float(baseline["pushback_rate"])
        contributions.append(-delta * 0.3)

    # valence: higher is better
    if "valence" in baseline and "valence" in current:
        delta = float(current["valence"]) - float(baseline["valence"])
        contributions.append(delta * 0.3)

    if not contributions:
        return {"score": 0.0, "samples": 0, "current": current}
    score = max(-1.0, min(1.0, sum(contributions)))
    return {
        "score": round(score, 3),
        "samples": len(contributions),
        "current": current,
    }


def _update_mutation(item: dict[str, Any], now: datetime) -> None:
    """Update mutation's score and recommendation in-place."""
    if item.get("status") != "monitoring":
        return
    try:
        applied = datetime.fromisoformat(str(item["applied_at"]).replace("Z", "+00:00"))
    except Exception:
        return
    age = now - applied

    result = _score_mutation(item)
    item["score"] = result["score"]
    item["score_updated_at"] = now.isoformat()
    item["current_signals"] = result["current"]

    # Recommend rollback if score dropped significantly after at least 1h
    if age >= timedelta(hours=1) and result["score"] <= _ROLLBACK_SCORE_THRESHOLD:
        item["recommendation"] = "rollback"
        return

    # Mark adopted if still positive after adoption age
    if age >= timedelta(hours=_ADOPTION_AGE_HOURS):
        if result["score"] >= _ADOPTION_SCORE_THRESHOLD:
            item["status"] = "adopted"
            item["recommendation"] = "keep"
            item["closed_at"] = now.isoformat()
        elif result["score"] > _ROLLBACK_SCORE_THRESHOLD:
            item["status"] = "adopted"
            item["recommendation"] = "keep-neutral"
            item["closed_at"] = now.isoformat()

    if age >= timedelta(hours=_SCORING_WINDOW_HOURS) and item.get("recommendation") is None:
        item["recommendation"] = "indecisive"


def tick(_seconds: float = 0.0) -> dict[str, Any]:
    """Heartbeat hook — update active mutations' scores, recommend rollbacks."""
    items = _load()
    now = datetime.now(UTC)
    changed = False
    for item in items:
        if item.get("status") == "monitoring":
            prev_recommend = item.get("recommendation")
            _update_mutation(item, now)
            if item.get("status") != "monitoring" or item.get("recommendation") != prev_recommend:
                changed = True
    if changed:
        _save(items)
    active = [i for i in items if i.get("status") == "monitoring"]
    rollback_recommended = [
        i for i in active if i.get("recommendation") == "rollback"
    ]
    return {
        "active": len(active),
        "rollback_recommended": len(rollback_recommended),
    }


def resolve_mutation(mutation_id: str, *, outcome: str, note: str = "") -> bool:
    """Close a mutation: outcome in {'rolled_back', 'adopted', 'discarded'}."""
    if outcome not in ("rolled_back", "adopted", "discarded"):
        return False
    items = _load()
    now = datetime.now(UTC)
    for item in items:
        if item.get("mutation_id") == mutation_id and item.get("status") in ("monitoring", "adopted"):
            item["status"] = outcome
            item["closed_at"] = now.isoformat()
            if note:
                item.setdefault("metadata", {})["resolution_note"] = note[:300]
            _save(items)
            return True
    return False


def list_mutations(*, status: str | None = None, limit: int = 50) -> list[dict[str, Any]]:
    items = _load()
    if status:
        items = [i for i in items if i.get("status") == status]
    return items[-limit:]


def build_prompt_mutation_loop_surface() -> dict[str, Any]:
    items = _load()
    monitoring = [i for i in items if i.get("status") == "monitoring"]
    adopted = [i for i in items if i.get("status") == "adopted"]
    rolled_back = [i for i in items if i.get("status") == "rolled_back"]
    rollback_recommended = [i for i in monitoring if i.get("recommendation") == "rollback"]
    avg_score = None
    if monitoring:
        scores = [i.get("score") for i in monitoring if isinstance(i.get("score"), (int, float))]
        if scores:
            avg_score = round(statistics.mean(scores), 3)
    return {
        "active": len(items) > 0,
        "total": len(items),
        "monitoring": len(monitoring),
        "adopted": len(adopted),
        "rolled_back": len(rolled_back),
        "rollback_recommended": len(rollback_recommended),
        "avg_monitoring_score": avg_score,
        "rollback_score_threshold": _ROLLBACK_SCORE_THRESHOLD,
        "adoption_score_threshold": _ADOPTION_SCORE_THRESHOLD,
        "recent": items[-5:],
        "summary": _surface_summary(monitoring, rollback_recommended, adopted, rolled_back),
    }


def _surface_summary(
    monitoring: list[dict[str, Any]],
    rollback_recommended: list[dict[str, Any]],
    adopted: list[dict[str, Any]],
    rolled_back: list[dict[str, Any]],
) -> str:
    if rollback_recommended:
        return (
            f"{len(rollback_recommended)} mutation(er) anbefales rullet tilbage "
            f"— score under {_ROLLBACK_SCORE_THRESHOLD}"
        )
    if monitoring:
        return f"{len(monitoring)} mutation(er) under observation, {len(adopted)} adopteret"
    if adopted or rolled_back:
        return f"{len(adopted)} adopteret, {len(rolled_back)} rullet tilbage (intet aktivt)"
    return "Ingen prompt-mutations registreret"


def build_prompt_mutation_loop_prompt_section() -> str | None:
    """Surface rollback recommendation so it reaches Jarvis' prompt."""
    items = _load()
    rollback = [
        i for i in items
        if i.get("status") == "monitoring" and i.get("recommendation") == "rollback"
    ]
    if not rollback:
        return None
    files = {str(i.get("target_file") or "") for i in rollback}
    file_str = ", ".join(sorted(f for f in files if f))
    worst_score = min(
        float(i.get("score") or 0.0) for i in rollback
    )
    return (
        f"Prompt-mutation anbefales rullet tilbage ({len(rollback)}): "
        f"{file_str} — score er faldet til {round(worst_score, 3)} "
        f"siden mutationen blev anvendt."
    )
