"""Agency Cartographer daemon.

Scans the local system for evidence that Jarvis' agency bridges are actually
wired. The goal is to keep Mission Control's Agency Map tied to runtime/code
truth instead of a purely hand-maintained checklist.
"""
from __future__ import annotations

import logging
import threading
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from core.runtime.state_store import load_json, save_json

logger = logging.getLogger(__name__)

_STATE_KEY = "agency_cartographer"
_REPO_ROOT = Path(__file__).resolve().parents[2]
_SCAN_INTERVAL_SECONDS = 900
_AUTO_TASK_MIN_SCORE = 125
_AUTO_TASK_KIND = "agency_bridge_repair"
_AUTO_TASK_ORIGIN = "agency-cartographer"

_THREAD: threading.Thread | None = None
_STOP = threading.Event()

# Awareness tracking: edge-status history for detecting stuck edges
_AGENCY_AWARENESS_KEY = "agency_cartographer_awareness"
_MAX_HISTORY_SCANS = 12  # ~3 hours at 15-min intervals


VISION_EDGES: tuple[dict[str, Any], ...] = (
    {
        "id": "senses-emotion",
        "title": "Senses -> Emotion",
        "target": "Senses -> Emotion",
        "summary": "Perceptual and sensory events should create emotional anchors/concepts.",
        "importance": 82,
        "agency_axes": ("sense", "feel", "remember"),
        "markers": (
            "capture_emotional_anchor",
            "on_sensory_recorded",
            "memory.sensory.recorded",
        ),
        "next_move": "Wire sensory/perceptual novelty into emotional anchors and concepts.",
    },
    {
        "id": "emotion-self-repair",
        "title": "Emotion -> Self-Repair",
        "target": "Emotion -> Self-Repair",
        "summary": "Repair should consult and record emotional context.",
        "importance": 78,
        "agency_axes": ("feel", "repair", "act"),
        "markers": (
            "_find_repair_emotional_precedents",
            "_process_emotional_gate_event",
            "self_repair.emotional_precedent_found",
        ),
        "next_move": "Let self-repair use emotional precedents before selecting repair actions.",
    },
    {
        "id": "self-repair-senses",
        "title": "Self-Repair -> Senses",
        "target": "Self-Repair -> Senses",
        "summary": "Repair actions should become perceptual/runtime changes.",
        "importance": 68,
        "agency_axes": ("repair", "sense", "witness"),
        "markers": (
            "self_repair.action_executed",
            "self-repair-action",
            "self-repair-rate-limit",
        ),
        "next_move": "Expose self-repair actions as perceptual events.",
    },
    {
        "id": "goals-emotion",
        "title": "Goals -> Emotion",
        "target": "Goals -> Emotion",
        "summary": "Goal creation/progress/completion should affect discrete emotion concepts.",
        "importance": 70,
        "agency_axes": ("intend", "feel", "remember"),
        "markers": (
            "on_goal_created",
            "on_goal_updated",
            "goal.completed",
        ),
        "next_move": "Bridge goal lifecycle events into joy, pride, and excitement concepts.",
    },
    {
        "id": "tools-memory-executive",
        "title": "Tools -> Memory -> Living Executive",
        "target": "Tools -> Memory -> Living Executive",
        "summary": "Tool outcomes should become durable precedents that shape later choices.",
        "importance": 92,
        "agency_axes": ("act", "remember", "choose"),
        "markers": (
            "record_tool_outcome_memory",
            "classify_tool_family",
            "_recent_memory_precedents",
            "choice_score",
        ),
        "next_move": "Persist tool outcomes and use them as executive choice precedents.",
    },
    {
        "id": "executive-tools",
        "title": "Living Executive -> Tools",
        "target": "Living Executive -> Tools",
        "summary": "Executive plans should become concrete runnable tool proposals.",
        "importance": 96,
        "agency_axes": ("choose", "act", "witness"),
        "markers": (
            "runnable_tool_proposals",
            "_runnable_tool_proposals",
            "living_executive.tool_plan_proposed",
        ),
        "next_move": "Turn executive recovery plans into runnable tool proposals.",
    },
    {
        "id": "hidden-runtime-mc",
        "title": "Hidden Runtime -> Mission Control",
        "target": "Hidden Runtime -> Mission Control",
        "summary": "Runtime influences that change behavior should be visible in MC.",
        "importance": 88,
        "agency_axes": ("witness", "integrity", "governance"),
        "markers": (
            "darkEdges",
            "_dark_edges",
            "partial-surface",
        ),
        "next_move": "Expose hidden behavior-shaping runtime edges in Mission Control.",
    },
)


def build_cartographer_snapshot(*, auto_enqueue: bool = False) -> dict[str, Any]:
    """Scan code markers and persist a fresh Agency Cartographer snapshot."""
    files = _candidate_files()
    edges = [_scan_edge(edge, files) for edge in VISION_EDGES]
    missing_or_partial = sorted(
        [edge for edge in edges if edge["status"] in {"missing", "partial"}],
        key=lambda edge: (
            -int(edge.get("priority_score") or 0),
            str(edge.get("title") or ""),
        ),
    )
    task_candidates = _rank_task_candidates(edges)
    recommended_next_task = task_candidates[0] if task_candidates else None
    auto_task = _maybe_enqueue_recommended_task(recommended_next_task) if auto_enqueue else {
        "enabled": False,
        "status": "not-requested",
    }
    snapshot = {
        "scannedAt": datetime.now(UTC).isoformat(),
        "mode": "agency-cartographer",
        "summary": {
            "vision_edges": len(edges),
            "connected": sum(1 for edge in edges if edge["status"] == "connected"),
            "partial": sum(1 for edge in edges if edge["status"] == "partial"),
            "missing": sum(1 for edge in edges if edge["status"] == "missing"),
            "task_candidates": len(task_candidates),
            "top_priority_score": (
                task_candidates[0]["priority_score"] if task_candidates else 0
            ),
        },
        "edges": edges,
        "nextMoves": [_next_move_from_edge(edge) for edge in missing_or_partial],
        "taskCandidates": task_candidates,
        "recommendedNextTask": recommended_next_task,
        "autoTask": auto_task,
    }
    save_json(_STATE_KEY, snapshot)
    # Record edge-status history for stuck-edge detection
    _record_awareness_history(edges)
    return snapshot


def get_cartographer_snapshot(*, refresh: bool = False) -> dict[str, Any]:
    if refresh:
        return build_cartographer_snapshot()
    snapshot = load_json(_STATE_KEY, {})
    summary = snapshot.get("summary") if isinstance(snapshot, dict) else None
    if (
        isinstance(snapshot, dict)
        and snapshot.get("edges")
        and isinstance(summary, dict)
        and "task_candidates" in summary
        and "recommendedNextTask" in snapshot
        and "autoTask" in snapshot
    ):
        return snapshot
    return build_cartographer_snapshot()


def start_agency_cartographer_daemon() -> None:
    global _THREAD
    if _THREAD is not None and _THREAD.is_alive():
        return
    _STOP.clear()
    _THREAD = threading.Thread(target=_loop, daemon=True, name="agency-cartographer")
    _THREAD.start()
    logger.info("agency_cartographer: daemon started")


def stop_agency_cartographer_daemon() -> None:
    _STOP.set()


def _loop() -> None:
    while not _STOP.is_set():
        try:
            build_cartographer_snapshot(auto_enqueue=True)
        except Exception as exc:
            logger.debug("agency_cartographer: scan failed: %s", exc)
            try:
                from core.services.daemon_health import note_error
                note_error("agency_cartographer", exc)
            except Exception:
                pass
        _STOP.wait(_SCAN_INTERVAL_SECONDS)
    logger.info("agency_cartographer: daemon stopped")


def _candidate_files() -> dict[str, str]:
    roots = (_REPO_ROOT / "core", _REPO_ROOT / "apps" / "ui" / "src")
    files: dict[str, str] = {}
    for root in roots:
        if not root.exists():
            continue
        for path in root.rglob("*"):
            if path.suffix not in {".py", ".jsx", ".js", ".ts", ".tsx"}:
                continue
            if path.name == "agency_cartographer.py":
                continue
            try:
                files[str(path.relative_to(_REPO_ROOT))] = path.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue
    return files


def _scan_edge(edge: dict[str, Any], files: dict[str, str]) -> dict[str, Any]:
    evidence: list[dict[str, str]] = []
    for marker in edge["markers"]:
        hit_path = _find_marker(str(marker), files)
        if hit_path:
            evidence.append({"marker": str(marker), "path": hit_path})
    ratio = len(evidence) / max(len(edge["markers"]), 1)
    status = "connected" if ratio >= 0.67 else "partial" if evidence else "missing"
    importance = int(edge.get("importance") or 50)
    agency_axes = tuple(str(axis) for axis in edge.get("agency_axes", ()))
    priority_score = _priority_score(
        status=status,
        confidence=ratio,
        importance=importance,
        agency_axes=agency_axes,
    )
    return {
        "id": str(edge["id"]),
        "title": str(edge["title"]),
        "target": str(edge["target"]),
        "summary": str(edge["summary"]),
        "status": status,
        "confidence": round(ratio, 2),
        "importance": importance,
        "agency_axes": list(agency_axes),
        "priority_score": priority_score,
        "priority_reason": _priority_reason(
            status=status,
            confidence=ratio,
            importance=importance,
            agency_axes=agency_axes,
        ),
        "evidence": evidence,
        "missing_markers": [
            str(marker)
            for marker in edge["markers"]
            if not any(item["marker"] == str(marker) for item in evidence)
        ],
        "next_move": str(edge["next_move"]),
    }


def _find_marker(marker: str, files: dict[str, str]) -> str:
    for path, text in files.items():
        if marker in text:
            return path
    return ""


def _next_move_from_edge(edge: dict[str, Any]) -> dict[str, str]:
    priority = _priority_label(int(edge.get("priority_score") or 0))
    return {
        "title": str(edge["title"]),
        "summary": str(edge["next_move"]),
        "target": str(edge["target"]),
        "priority": priority,
        "source": "agency-cartographer",
        "priority_score": str(edge.get("priority_score") or 0),
        "reason": str(edge.get("priority_reason") or ""),
    }


def _rank_task_candidates(edges: list[dict[str, Any]]) -> list[dict[str, Any]]:
    candidates = [
        _task_candidate_from_edge(edge)
        for edge in edges
        if edge.get("status") in {"missing", "partial"}
    ]
    candidates.sort(
        key=lambda item: (
            -int(item.get("priority_score") or 0),
            str(item.get("title") or ""),
        )
    )
    return candidates


def _task_candidate_from_edge(edge: dict[str, Any]) -> dict[str, Any]:
    score = int(edge.get("priority_score") or 0)
    return {
        "id": f"agency-{edge.get('id')}",
        "title": str(edge.get("title") or ""),
        "goal": str(edge.get("next_move") or ""),
        "scope": str(edge.get("target") or ""),
        "task_kind": _AUTO_TASK_KIND,
        "priority": _priority_label(score),
        "priority_score": score,
        "reason": str(edge.get("priority_reason") or ""),
        "status": str(edge.get("status") or ""),
        "confidence": edge.get("confidence", 0),
        "missing_markers": list(edge.get("missing_markers") or []),
        "evidence_count": len(edge.get("evidence") or []),
        "source": "agency-cartographer",
    }


def _maybe_enqueue_recommended_task(candidate: dict[str, Any] | None) -> dict[str, Any]:
    if not candidate:
        return {"enabled": True, "status": "no-candidate"}

    score = int(candidate.get("priority_score") or 0)
    if score < _AUTO_TASK_MIN_SCORE:
        return {
            "enabled": True,
            "status": "below-threshold",
            "threshold": _AUTO_TASK_MIN_SCORE,
            "priority_score": score,
        }

    duplicate = _find_existing_agency_task(candidate)
    if duplicate:
        return {
            "enabled": True,
            "status": "duplicate-present",
            "task_id": str(duplicate.get("task_id") or ""),
            "task_status": str(duplicate.get("status") or ""),
            "priority_score": score,
        }

    try:
        from core.services.runtime_tasks import create_task

        task = create_task(
            kind=_AUTO_TASK_KIND,
            goal=str(candidate.get("goal") or candidate.get("title") or ""),
            scope=str(candidate.get("scope") or ""),
            origin=_AUTO_TASK_ORIGIN,
            priority=_runtime_task_priority(str(candidate.get("priority") or "")),
            owner="jarvis",
        )
        _publish_auto_task_event(candidate, task)
        return {
            "enabled": True,
            "status": "enqueued",
            "task_id": str(task.get("task_id") or ""),
            "priority_score": score,
        }
    except Exception as exc:
        logger.debug("agency_cartographer: auto task enqueue failed: %s", exc)
        return {
            "enabled": True,
            "status": "enqueue-failed",
            "error": f"{type(exc).__name__}: {exc}"[:300],
            "priority_score": score,
        }


def _find_existing_agency_task(candidate: dict[str, Any]) -> dict[str, Any] | None:
    try:
        from core.services.runtime_tasks import list_tasks

        scope = str(candidate.get("scope") or "").strip()
        goal = str(candidate.get("goal") or "").strip()
        for status in ("queued", "running", "blocked"):
            for task in list_tasks(status=status, kind=_AUTO_TASK_KIND, limit=50):
                if str(task.get("scope") or "").strip() == scope:
                    return task
                if str(task.get("goal") or "").strip() == goal:
                    return task
    except Exception:
        return None
    return None


def _runtime_task_priority(priority: str) -> str:
    normalized = str(priority or "").strip().lower()
    if normalized == "critical":
        return "high"
    if normalized in {"high", "medium", "low"}:
        return normalized
    return "medium"


def _publish_auto_task_event(
    candidate: dict[str, Any],
    task: dict[str, object],
) -> None:
    try:
        from core.eventbus.bus import event_bus

        event_bus.publish(
            "agency_cartographer.task_enqueued",
            {
                "task_id": task.get("task_id"),
                "title": candidate.get("title"),
                "scope": candidate.get("scope"),
                "priority_score": candidate.get("priority_score"),
                "reason": candidate.get("reason"),
            },
        )
    except Exception:
        return


def _priority_score(
    *,
    status: str,
    confidence: float,
    importance: int,
    agency_axes: tuple[str, ...],
) -> int:
    if status == "connected":
        return 0
    gap_score = 100 if status == "missing" else 58
    confidence_gap = int(round((1.0 - max(0.0, min(confidence, 1.0))) * 28))
    axis_bonus = 0
    for axis in agency_axes:
        axis_bonus += {
            "act": 9,
            "choose": 9,
            "witness": 7,
            "integrity": 7,
            "governance": 6,
            "repair": 6,
            "remember": 5,
            "feel": 4,
            "sense": 4,
            "intend": 4,
        }.get(axis, 2)
    raw = gap_score + int(importance * 0.75) + min(axis_bonus, 24) + confidence_gap
    return max(0, min(raw, 200))


def _priority_label(score: int) -> str:
    if score >= 165:
        return "critical"
    if score >= 125:
        return "high"
    if score >= 80:
        return "medium"
    if score > 0:
        return "low"
    return "done"


def _priority_reason(
    *,
    status: str,
    confidence: float,
    importance: int,
    agency_axes: tuple[str, ...],
) -> str:
    if status == "connected":
        return "Bridge has enough code/runtime evidence right now."
    gap = "no evidence" if status == "missing" else f"{confidence:.0%} evidence"
    axes = ", ".join(agency_axes) if agency_axes else "general agency"
    return (
        f"{status} bridge with {gap}; importance {importance}/100; "
        f"touches {axes}."
    )


# ─── Live Awareness (Agency Cartographer → prompt feedback) ───


def build_agency_cartographer_awareness_section() -> str | None:
    """Build a compact 'Agency Bridges' awareness section for the heartbeat prompt.

    Returns a formatted markdown block showing:
      - Overall bridge health (connected/partial/missing)
      - The top 1-2 stuck edges (missing/partial for multiple scans)
      - A concrete next-move for each stuck edge
    Returns None if no snapshot data is available.
    """
    snapshot = get_cartographer_snapshot(refresh=False)
    if not isinstance(snapshot, dict) or not snapshot.get("edges"):
        return None

    summary = snapshot.get("summary") or {}
    edges: list[dict[str, Any]] = snapshot.get("edges") or []
    next_moves: list[dict[str, str]] = snapshot.get("nextMoves") or []

    # Find stuck edges (same status for >= 3 scans; history recorded by build_cartographer_snapshot)
    stuck = _compute_stuck_edges(edges)

    total = summary.get("vision_edges", 0)
    connected = summary.get("connected", 0)
    partial = summary.get("partial", 0)
    missing = summary.get("missing", 0)

    lines: list[str] = []
    lines.append(f"🧭 **Agency Bridges:** {connected}/{total} connected | {partial} partial | {missing} missing")

    # Show stuck edges with next moves
    if stuck:
        lines.append("")
        for edge_id, status, stuck_count in stuck[:2]:
            edge = next((e for e in edges if e.get("id") == edge_id), None)
            if not edge:
                continue
            next_move = next(
                (nm.get("summary") for nm in next_moves if nm.get("title") == edge.get("title")),
                edge.get("next_move", ""),
            )
            label = "🔴" if status == "missing" else "🟡"
            lines.append(
                f"{label} **{edge.get('title', edge_id)}** "
                f"(stuck {stuck_count} scans) — {next_move}"
            )

    # If nothing stuck, show the highest-priority next move
    elif next_moves:
        lines.append("")
        top = next_moves[0]
        lines.append(f"🔄 **Next move:** {top.get('summary', '')}")

    result = "\n".join(lines)
    return result if result.strip() else None


def _record_awareness_history(edges: list[dict[str, Any]]) -> None:
    """Record current edge statuses into awareness history for stuck detection."""
    history: dict[str, list[str]] = load_json(_AGENCY_AWARENESS_KEY, {})
    now_iso = datetime.now(UTC).isoformat()
    for edge in edges:
        edge_id = str(edge.get("id", ""))
        status = str(edge.get("status", "unknown"))
        if edge_id not in history:
            history[edge_id] = []
        history[edge_id].append(status)
        # Trim to max history length
        if len(history[edge_id]) > _MAX_HISTORY_SCANS:
            history[edge_id] = history[edge_id][-_MAX_HISTORY_SCANS:]
    # Trim stale edge entries
    active_ids = {str(e.get("id", "")) for e in edges}
    for edge_id in list(history.keys()):
        if edge_id not in active_ids:
            del history[edge_id]
    save_json(_AGENCY_AWARENESS_KEY, history)


def _compute_stuck_edges(
    edges: list[dict[str, Any]],
) -> list[tuple[str, str, int]]:
    """Return edges whose status hasn't changed in >= 3 scans.

    Returns list of (edge_id, status, stuck_count) sorted by priority_score descending.
    """
    history: dict[str, list[str]] = load_json(_AGENCY_AWARENESS_KEY, {})
    stuck: list[tuple[str, str, int]] = []
    for edge in edges:
        edge_id = str(edge.get("id", ""))
        status = str(edge.get("status", "unknown"))
        if status == "connected":
            continue
        hist = history.get(edge_id, [status])
        # Count consecutive same status from the end
        consecutive = 0
        for s in reversed(hist):
            if s == status:
                consecutive += 1
            else:
                break
        if consecutive >= 3:
            stuck.append((edge_id, status, consecutive))
    # Sort by priority
    edge_map = {str(e.get("id", "")): e for e in edges}
    stuck.sort(
        key=lambda item: (
            -int(edge_map.get(item[0], {}).get("priority_score", 0) if item[0] in edge_map else 0),
            -item[2],
        ),
    )
    return stuck
