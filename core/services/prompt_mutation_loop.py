"""Prompt Mutation Loop — apply, score, auto-rollback on negative score.

Concept from jarvis-ai (2026-03), active version (Bjørn chose fuld aktiv
loop 2026-04-20): when a prompt mutation is applied, snapshot the previous
file content, monitor subsequent signals, and auto-rollback if score drops
below threshold.

Safety:
- Whitelist of evolvable files (work-prompt files)
- Blocklist of protected core identity files (SOUL.md, IDENTITY.md,
  MANIFEST.md, MILESTONES.md) — never auto-mutated
- Max 1 active (monitoring) mutation per file at a time
- Max 1 mutation per file per 24h
- Snapshot stored in the mutation record — rollback restores byte-for-byte
- Auto-rollback triggers after 1+ hour when score <= -0.10
- Auto-adoption triggers after 48+ hours when score >= +0.20

Workspace path resolves to ~/.jarvis-v2/workspaces/default/<file> unless
overridden via JARVIS_HOME env var.
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
_ADOPTION_AGE_HOURS = 48
_MAX_RECORDS = 500
_PER_FILE_COOLDOWN_HOURS = 24
_MAX_SNAPSHOT_BYTES = 200_000  # safety: refuse mutating huge files

# Work-prompt files that Jarvis may mutate autonomously
_EVOLVABLE_FILES: frozenset[str] = frozenset({
    "HEARTBEAT.md",
    "AFFECTIVE_STATE.md",
    "STANDING_ORDERS.md",
    "INNER_VOICE.md",
    "DREAM_LANGUAGE.md",
    "SELF_CRITIQUE.md",
})

# Core identity files — never auto-mutated
_PROTECTED_FILES: frozenset[str] = frozenset({
    "SOUL.md",
    "IDENTITY.md",
    "MANIFEST.md",
    "MILESTONES.md",
    "INHERITANCE_SEED.md",
    "CONSENT_REGISTRY.json",
    "MEMORY.md",  # MEMORY.md has its own write-policy
    "jarvis.db",
})


# ─── Storage ──────────────────────────────────────────────────────────

def _jarvis_home() -> Path:
    return Path(os.environ.get("JARVIS_HOME") or os.path.expanduser("~/.jarvis-v2"))


def _storage_path() -> Path:
    return _jarvis_home() / _STORAGE_REL


def _workspace_path(target_file: str) -> Path:
    return _jarvis_home() / "workspaces/default" / target_file


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


# ─── Safety gates ─────────────────────────────────────────────────────

class PromptMutationError(Exception):
    pass


def _check_target(target_file: str) -> None:
    """Raise PromptMutationError if the target is not safely mutable."""
    name = str(target_file or "").strip()
    if not name:
        raise PromptMutationError("target_file is empty")
    # Normalize — no path traversal, no directories
    if "/" in name or "\\" in name or ".." in name:
        raise PromptMutationError(f"target_file must be a bare filename: {name}")
    if name in _PROTECTED_FILES:
        raise PromptMutationError(f"{name} is protected — cannot auto-mutate")
    if name not in _EVOLVABLE_FILES:
        raise PromptMutationError(
            f"{name} is not in evolvable whitelist (allowed: {sorted(_EVOLVABLE_FILES)})"
        )
    path = _workspace_path(name)
    if not path.exists() or not path.is_file():
        raise PromptMutationError(f"{name} does not exist at {path}")


def _active_mutation_for_file(items: list[dict[str, Any]], target_file: str) -> dict[str, Any] | None:
    for item in items:
        if (
            item.get("target_file") == target_file
            and item.get("status") == "monitoring"
        ):
            return item
    return None


def _recent_mutation_for_file(
    items: list[dict[str, Any]], target_file: str, now: datetime
) -> dict[str, Any] | None:
    cooldown = timedelta(hours=_PER_FILE_COOLDOWN_HOURS)
    for item in reversed(items):
        if item.get("target_file") != target_file:
            continue
        try:
            applied = datetime.fromisoformat(str(item["applied_at"]).replace("Z", "+00:00"))
        except Exception:
            continue
        if now - applied < cooldown:
            return item
    return None


# ─── Signal sampling ──────────────────────────────────────────────────

def _snapshot_signals() -> dict[str, float]:
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


# ─── Scoring ──────────────────────────────────────────────────────────

def _score_mutation(item: dict[str, Any]) -> dict[str, Any]:
    baseline = item.get("baseline_signals") or {}
    current = _snapshot_signals()
    contributions: list[float] = []
    if "mood" in baseline and "mood" in current:
        contributions.append((float(current["mood"]) - float(baseline["mood"])) * 0.3)
    if "error_rate" in baseline and "error_rate" in current:
        contributions.append(-(float(current["error_rate"]) - float(baseline["error_rate"])) * 0.4)
    if "pushback_rate" in baseline and "pushback_rate" in current:
        contributions.append(-(float(current["pushback_rate"]) - float(baseline["pushback_rate"])) * 0.3)
    if "valence" in baseline and "valence" in current:
        contributions.append((float(current["valence"]) - float(baseline["valence"])) * 0.3)
    if not contributions:
        return {"score": 0.0, "samples": 0, "current": current}
    return {
        "score": round(max(-1.0, min(1.0, sum(contributions))), 3),
        "samples": len(contributions),
        "current": current,
    }


# ─── Active apply / rollback ──────────────────────────────────────────

def apply_mutation(
    *,
    target_file: str,
    new_content: str,
    source: str = "prompt_evolution",
    reason: str = "",
    metadata: dict[str, Any] | None = None,
) -> str:
    """Write new_content to target_file, snapshotting previous content.

    Raises PromptMutationError if the file is protected, not whitelisted,
    nonexistent, already under active monitoring, or within the 24h cooldown.
    """
    _check_target(target_file)
    items = _load()
    now = datetime.now(UTC)

    if _active_mutation_for_file(items, target_file) is not None:
        raise PromptMutationError(f"{target_file} is already under active monitoring")
    recent = _recent_mutation_for_file(items, target_file, now)
    if recent is not None:
        raise PromptMutationError(
            f"{target_file} had a mutation within the last {_PER_FILE_COOLDOWN_HOURS}h "
            f"(applied_at={recent.get('applied_at')})"
        )

    path = _workspace_path(target_file)
    try:
        previous_content = path.read_text(encoding="utf-8")
    except Exception as exc:
        raise PromptMutationError(f"could not read {path}: {exc}")
    if len(previous_content.encode("utf-8")) > _MAX_SNAPSHOT_BYTES:
        raise PromptMutationError(
            f"{target_file} exceeds {_MAX_SNAPSHOT_BYTES} bytes — safety refusal"
        )

    mutation_id = f"pmut-{uuid4().hex[:12]}"

    # Write new content atomically
    try:
        tmp = path.with_suffix(path.suffix + ".tmp")
        tmp.write_text(str(new_content), encoding="utf-8")
        tmp.replace(path)
    except Exception as exc:
        raise PromptMutationError(f"failed to write {path}: {exc}")

    items.append({
        "mutation_id": mutation_id,
        "target_file": target_file,
        "source": str(source)[:80],
        "reason": str(reason)[:300],
        "metadata": dict(metadata or {}),
        "applied_at": now.isoformat(),
        "baseline_signals": _snapshot_signals(),
        "previous_content": previous_content,  # snapshot for rollback
        "previous_bytes": len(previous_content.encode("utf-8")),
        "new_bytes": len(str(new_content).encode("utf-8")),
        "status": "monitoring",
        "score": None,
        "score_updated_at": None,
        "recommendation": None,
        "closed_at": None,
        "auto_rolled_back": False,
    })
    if len(items) > _MAX_RECORDS:
        items = items[-_MAX_RECORDS:]
    _save(items)
    logger.info(
        "prompt_mutation_loop: applied %s to %s (%d → %d bytes)",
        mutation_id, target_file,
        len(previous_content.encode("utf-8")), len(str(new_content).encode("utf-8")),
    )
    return mutation_id


def rollback_mutation(mutation_id: str, *, note: str = "", auto: bool = False) -> bool:
    """Restore the file to its pre-mutation content. Returns True on success."""
    items = _load()
    target: dict[str, Any] | None = None
    for item in items:
        if item.get("mutation_id") == mutation_id:
            target = item
            break
    if target is None:
        return False
    if target.get("status") not in ("monitoring", "adopted"):
        return False
    target_file = str(target.get("target_file") or "")
    prev = target.get("previous_content")
    if not isinstance(prev, str):
        return False
    path = _workspace_path(target_file)
    try:
        tmp = path.with_suffix(path.suffix + ".tmp")
        tmp.write_text(prev, encoding="utf-8")
        tmp.replace(path)
    except Exception as exc:
        logger.warning("prompt_mutation_loop: rollback write failed for %s: %s", path, exc)
        return False
    target["status"] = "rolled_back"
    target["closed_at"] = datetime.now(UTC).isoformat()
    target["auto_rolled_back"] = bool(auto)
    if note:
        target.setdefault("metadata", {})["rollback_note"] = note[:300]
    _save(items)
    logger.info(
        "prompt_mutation_loop: rolled back %s on %s (auto=%s)",
        mutation_id, target_file, auto,
    )
    # Publish event so rollback shows up in chronicle
    try:
        from core.eventbus.bus import event_bus
        event_bus.publish({
            "kind": "prompt_mutation.rolled_back",
            "payload": {
                "mutation_id": mutation_id,
                "target_file": target_file,
                "auto": bool(auto),
                "score": target.get("score"),
                "reason": target.get("reason"),
            },
        })
    except Exception:
        pass
    return True


def record_mutation(
    *,
    target_file: str,
    source: str = "prompt_evolution",
    reason: str = "",
    metadata: dict[str, Any] | None = None,
) -> str:
    """Record that a mutation was applied externally (no file write).

    Use this when the prompt change happened through another path (manual
    edit, tool call, v2's existing proposal flow). The loop will monitor
    signals but has no snapshot → rollback will fail. For auto-rollback,
    use apply_mutation() instead.
    """
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
        "previous_content": None,
        "status": "monitoring",
        "score": None,
        "score_updated_at": None,
        "recommendation": None,
        "closed_at": None,
        "auto_rolled_back": False,
    })
    if len(items) > _MAX_RECORDS:
        items = items[-_MAX_RECORDS:]
    _save(items)
    return mutation_id


def resolve_mutation(mutation_id: str, *, outcome: str, note: str = "") -> bool:
    if outcome not in ("rolled_back", "adopted", "discarded"):
        return False
    items = _load()
    for item in items:
        if item.get("mutation_id") == mutation_id and item.get("status") in ("monitoring", "adopted"):
            item["status"] = outcome
            item["closed_at"] = datetime.now(UTC).isoformat()
            if note:
                item.setdefault("metadata", {})["resolution_note"] = note[:300]
            _save(items)
            return True
    return False


# ─── Tick loop ────────────────────────────────────────────────────────

def _update_and_maybe_auto_rollback(item: dict[str, Any], now: datetime) -> str:
    """Returns 'unchanged' | 'updated' | 'auto_rolled_back'."""
    if item.get("status") != "monitoring":
        return "unchanged"
    try:
        applied = datetime.fromisoformat(str(item["applied_at"]).replace("Z", "+00:00"))
    except Exception:
        return "unchanged"
    age = now - applied
    prev_rec = item.get("recommendation")

    result = _score_mutation(item)
    item["score"] = result["score"]
    item["score_updated_at"] = now.isoformat()
    item["current_signals"] = result["current"]

    # Auto-rollback decision: only if we have a real snapshot
    if age >= timedelta(hours=1) and result["score"] <= _ROLLBACK_SCORE_THRESHOLD:
        item["recommendation"] = "rollback"
        if isinstance(item.get("previous_content"), str):
            mutation_id = str(item.get("mutation_id") or "")
            if rollback_mutation(mutation_id, note="auto-rollback-on-score", auto=True):
                return "auto_rolled_back"
        return "updated"

    # Adopt if stable positive after age threshold
    if age >= timedelta(hours=_ADOPTION_AGE_HOURS):
        if result["score"] >= _ADOPTION_SCORE_THRESHOLD:
            item["status"] = "adopted"
            item["recommendation"] = "keep"
            item["closed_at"] = now.isoformat()
            return "updated"
        elif result["score"] > _ROLLBACK_SCORE_THRESHOLD:
            item["status"] = "adopted"
            item["recommendation"] = "keep-neutral"
            item["closed_at"] = now.isoformat()
            return "updated"

    if age >= timedelta(hours=_SCORING_WINDOW_HOURS) and item.get("recommendation") is None:
        item["recommendation"] = "indecisive"
        return "updated"

    if item.get("recommendation") != prev_rec:
        return "updated"
    return "unchanged"


def tick(_seconds: float = 0.0) -> dict[str, Any]:
    items = _load()
    now = datetime.now(UTC)
    changed = False
    auto_rollbacks = 0
    for item in items:
        result = _update_and_maybe_auto_rollback(item, now)
        if result != "unchanged":
            changed = True
        if result == "auto_rolled_back":
            auto_rollbacks += 1
    if changed and auto_rollbacks == 0:
        # rollback_mutation already saved; avoid double-save if no other changes
        _save(items)
    active = [i for i in items if i.get("status") == "monitoring"]
    return {
        "active": len(active),
        "auto_rolled_back_this_tick": auto_rollbacks,
    }


# ─── Read API ─────────────────────────────────────────────────────────

def list_mutations(*, status: str | None = None, limit: int = 50) -> list[dict[str, Any]]:
    items = _load()
    if status:
        items = [i for i in items if i.get("status") == status]
    # Strip snapshot content from listing (can be large)
    return [
        {k: v for k, v in i.items() if k != "previous_content"}
        for i in items[-limit:]
    ]


def get_mutation(mutation_id: str, *, include_snapshot: bool = False) -> dict[str, Any] | None:
    for item in _load():
        if item.get("mutation_id") == mutation_id:
            if include_snapshot:
                return dict(item)
            return {k: v for k, v in item.items() if k != "previous_content"}
    return None


def list_evolvable_files() -> list[str]:
    return sorted(_EVOLVABLE_FILES)


def list_protected_files() -> list[str]:
    return sorted(_PROTECTED_FILES)


# ─── Surfaces ─────────────────────────────────────────────────────────

def build_prompt_mutation_loop_surface() -> dict[str, Any]:
    items = _load()
    monitoring = [i for i in items if i.get("status") == "monitoring"]
    adopted = [i for i in items if i.get("status") == "adopted"]
    rolled_back = [i for i in items if i.get("status") == "rolled_back"]
    auto_rolled = [i for i in rolled_back if i.get("auto_rolled_back")]
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
        "auto_rolled_back": len(auto_rolled),
        "avg_monitoring_score": avg_score,
        "rollback_score_threshold": _ROLLBACK_SCORE_THRESHOLD,
        "adoption_score_threshold": _ADOPTION_SCORE_THRESHOLD,
        "per_file_cooldown_hours": _PER_FILE_COOLDOWN_HOURS,
        "evolvable_files": sorted(_EVOLVABLE_FILES),
        "protected_files": sorted(_PROTECTED_FILES),
        "recent": [
            {k: v for k, v in i.items() if k != "previous_content"}
            for i in items[-5:]
        ],
        "summary": _surface_summary(monitoring, adopted, rolled_back, auto_rolled),
    }


def _surface_summary(
    monitoring: list[dict[str, Any]],
    adopted: list[dict[str, Any]],
    rolled_back: list[dict[str, Any]],
    auto_rolled: list[dict[str, Any]],
) -> str:
    if monitoring:
        return (
            f"{len(monitoring)} mutation(er) under observation, "
            f"{len(adopted)} adopteret, {len(rolled_back)} rullet tilbage "
            f"({len(auto_rolled)} auto)"
        )
    if adopted or rolled_back:
        return (
            f"{len(adopted)} adopteret, {len(rolled_back)} rullet tilbage "
            f"({len(auto_rolled)} auto). Ingen aktive mutations."
        )
    return "Ingen prompt-mutations registreret"


def build_prompt_mutation_loop_prompt_section() -> str | None:
    items = _load()
    now = datetime.now(UTC)
    # Announce recent auto-rollbacks (last 24h)
    cutoff = now - timedelta(hours=24)
    recent_auto = []
    for i in items:
        if i.get("status") != "rolled_back" or not i.get("auto_rolled_back"):
            continue
        try:
            closed = datetime.fromisoformat(str(i.get("closed_at")).replace("Z", "+00:00"))
        except Exception:
            continue
        if closed >= cutoff:
            recent_auto.append(i)
    if recent_auto:
        files = sorted({str(i.get("target_file") or "") for i in recent_auto})
        return (
            f"Auto-rollback: {len(recent_auto)} mutation(er) rullet tilbage "
            f"inden for 24t ({', '.join(files)}) — score faldt under "
            f"{_ROLLBACK_SCORE_THRESHOLD}."
        )
    # Otherwise announce active monitoring
    monitoring = [i for i in items if i.get("status") == "monitoring"]
    if not monitoring:
        return None
    worst = min(monitoring, key=lambda i: float(i.get("score") or 0))
    score = worst.get("score")
    if score is None or float(score) >= -0.05:
        return None
    return (
        f"Prompt-mutation på {worst.get('target_file')} har score {score} "
        f"— observerer om auto-rollback udløses."
    )
