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

_THREAD: threading.Thread | None = None
_STOP = threading.Event()


VISION_EDGES: tuple[dict[str, Any], ...] = (
    {
        "id": "senses-emotion",
        "title": "Senses -> Emotion",
        "target": "Senses -> Emotion",
        "summary": "Perceptual and sensory events should create emotional anchors/concepts.",
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
        "markers": (
            "darkEdges",
            "_dark_edges",
            "partial-surface",
        ),
        "next_move": "Expose hidden behavior-shaping runtime edges in Mission Control.",
    },
)


def build_cartographer_snapshot() -> dict[str, Any]:
    """Scan code markers and persist a fresh Agency Cartographer snapshot."""
    files = _candidate_files()
    edges = [_scan_edge(edge, files) for edge in VISION_EDGES]
    missing_or_partial = [edge for edge in edges if edge["status"] in {"missing", "partial"}]
    snapshot = {
        "scannedAt": datetime.now(UTC).isoformat(),
        "mode": "agency-cartographer",
        "summary": {
            "vision_edges": len(edges),
            "connected": sum(1 for edge in edges if edge["status"] == "connected"),
            "partial": sum(1 for edge in edges if edge["status"] == "partial"),
            "missing": sum(1 for edge in edges if edge["status"] == "missing"),
        },
        "edges": edges,
        "nextMoves": [_next_move_from_edge(edge) for edge in missing_or_partial],
    }
    save_json(_STATE_KEY, snapshot)
    return snapshot


def get_cartographer_snapshot(*, refresh: bool = False) -> dict[str, Any]:
    if refresh:
        return build_cartographer_snapshot()
    snapshot = load_json(_STATE_KEY, {})
    if isinstance(snapshot, dict) and snapshot.get("edges"):
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
            build_cartographer_snapshot()
        except Exception as exc:
            logger.debug("agency_cartographer: scan failed: %s", exc)
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
    return {
        "id": str(edge["id"]),
        "title": str(edge["title"]),
        "target": str(edge["target"]),
        "summary": str(edge["summary"]),
        "status": status,
        "confidence": round(ratio, 2),
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
    priority = "high" if edge["status"] == "missing" else "medium"
    return {
        "title": str(edge["title"]),
        "summary": str(edge["next_move"]),
        "target": str(edge["target"]),
        "priority": priority,
        "source": "agency-cartographer",
    }
