"""System Cartographer — broad map of Jarvis' runtime and inner layers.

This is wider than the Agency Map vision edges. It inventories code/runtime
surfaces so Jarvis can ask "what exists in me, what emits, what is visible, and
what is probably still dark?"
"""
from __future__ import annotations

import re
import logging
import threading
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parents[2]
_AUTO_TASK_MIN_SCORE = 75
_AUTO_TASK_KIND = "observability_bridge_repair"
_AUTO_TASK_ORIGIN = "system-cartographer"
_THEATER_AUTO_TASK_MIN_SCORE = 120
_THEATER_AUTO_TASK_KIND = "theater_refactor"
_THEATER_AUTO_TASK_ORIGIN = "theater-audit"
_SCAN_INTERVAL_SECONDS = 900

logger = logging.getLogger(__name__)
_THREAD: threading.Thread | None = None
_STOP = threading.Event()

_PUBLISH_RE = re.compile(r"event_bus\.publish\(\s*f?[\"']([^\"']+)[\"']")
_EMIT_RE = re.compile(r"emit\(\s*f?[\"']([^\"']+)[\"']")
_SURFACE_RE = re.compile(r"def\s+(build_[a-zA-Z0-9_]*surface)\s*\(")
_TOOL_RE = re.compile(r"[\"']name[\"']\s*:\s*[\"']([^\"']+)[\"']")


def build_system_cartographer_surface(*, auto_enqueue: bool = False) -> dict[str, Any]:
    files = _service_files()
    services = [_service_node(path, text) for path, text in files.items()]
    services.sort(key=lambda item: str(item["id"]))
    daemons = _daemon_nodes()
    surfaces = _surface_nodes(services)
    event_families = _event_family_nodes(services)
    causal = _causal_runtime_evidence()
    tool_count = _tool_count()
    edges = _edges(
        services=services,
        daemons=daemons,
        surfaces=surfaces,
        event_families=event_families,
        causal=causal,
    )
    theater = _theater_audit_surface()
    dark_edges = _rank_dark_edges(_dark_edges(services), causal=causal, daemons=daemons)
    recommended_observability_task = (
        _observability_task_from_dark_edge(dark_edges[0]) if dark_edges else None
    )
    auto_task = (
        _maybe_enqueue_observability_task(recommended_observability_task)
        if auto_enqueue
        else {"enabled": False, "status": "not-requested"}
    )
    theater_auto_task = (
        _maybe_enqueue_theater_task(theater.get("recommendedTheaterTask"))
        if auto_enqueue and isinstance(theater, dict)
        else {"enabled": False, "status": "not-requested"}
    )
    coverage = _coverage_summary(services)
    system_health = _system_health_from_jarvis_perspective(
        dark_edges=dark_edges,
        coverage=coverage,
        theater=theater,
        recommended=recommended_observability_task,
    )
    return {
        "fetchedAt": datetime.now(UTC).isoformat(),
        "mode": "system-cartographer-v1",
        "summary": {
            "services": len(services),
            "daemons": len(daemons),
            "surfaces": len(surfaces),
            "event_families": len(event_families),
            "edges": len(edges),
            "dark_edges": len(dark_edges),
            "tools": tool_count,
            "observed_events": causal.get("event_count", 0),
            "observed_causal_edges": causal.get("edge_count", 0),
            "observed_causal_family_edges": len(causal.get("family_edges") or []),
            "avg_causal_coverage_score": coverage["avg_score"],
            "low_coverage_services": coverage["low_count"],
            "theater_findings": (theater.get("summary") or {}).get("findings", 0),
            "theater_high_risk": (theater.get("summary") or {}).get("high_risk", 0),
        },
        "nodes": {
            "services": services,
            "daemons": daemons,
            "surfaces": surfaces,
            "event_families": event_families,
        },
        "edges": edges,
        "darkEdges": dark_edges,
        "causalRuntime": causal,
        "recommendedObservabilityTask": recommended_observability_task,
        "autoTask": auto_task,
        "theaterAutoTask": theater_auto_task,
        "coverage": coverage,
        "systemHealth": system_health,
        "theaterAudit": theater,
        "notes": [
            "Phase 1 is code/runtime inventory, not proof of causal influence.",
            "Phase 2 adds eventbus/causal_edges runtime evidence.",
            "Phase 3 adds theater-risk audit for narrative-first inner-life prompts.",
            "Next phase should persist deltas over time and rank missing witness surfaces.",
        ],
    }


def start_system_cartographer_daemon() -> None:
    global _THREAD
    if _THREAD is not None and _THREAD.is_alive():
        return
    _STOP.clear()
    _THREAD = threading.Thread(target=_loop, daemon=True, name="system-cartographer")
    _THREAD.start()
    logger.info("system_cartographer: daemon started")


def stop_system_cartographer_daemon() -> None:
    _STOP.set()


def _observe_to_central(surface: dict[str, Any]) -> None:
    """System-cluster: MELD kartografens kort til Den Intelligente Central (self-safe).

    Kartografen kortlagde + triagerede allerede systemet (dark edges, auto-enqueued repair-
    tasks til Jarvis) — men Centralen så det aldrig. Nu ser den systemkortet ÉT sted: services,
    dark edges, health, theater-risiko, og hvilket hul der blev auto-enqueued vs anbefalet.
    Det er hele pointen: Centralen kortlægger systemet for os og Jarvis."""
    try:
        from core.services.central_core import central
        summary = surface.get("summary") or {}
        health = surface.get("systemHealth") or {}
        auto = surface.get("autoTask") or {}
        rec = surface.get("recommendedObservabilityTask") or {}
        central().observe({
            "cluster": "system", "nerve": "cartographer",
            "services": summary.get("services"),
            "daemons": summary.get("daemons"),
            "dark_edges": summary.get("dark_edges"),
            "low_coverage": summary.get("low_coverage_services"),
            "theater_high_risk": summary.get("theater_high_risk"),
            "tools": summary.get("tools"),
            "health_state": health.get("state"),
            "auto_task_status": auto.get("status"),
            "auto_task_id": auto.get("task_id"),
            "recommended_next": rec.get("title"),
        })
    except Exception:
        pass


def _loop() -> None:
    while not _STOP.is_set():
        try:
            surface = build_system_cartographer_surface(auto_enqueue=True)
            _observe_to_central(surface)
        except Exception as exc:
            logger.debug("system_cartographer: scan failed: %s", exc)
        _STOP.wait(_SCAN_INTERVAL_SECONDS)
    logger.info("system_cartographer: daemon stopped")


def _service_files() -> dict[str, str]:
    root = _REPO_ROOT / "core" / "services"
    result: dict[str, str] = {}
    for path in root.glob("*.py"):
        if path.name.startswith("__"):
            continue
        try:
            result[str(path.relative_to(_REPO_ROOT))] = path.read_text(
                encoding="utf-8",
                errors="ignore",
            )
        except Exception:
            continue
    return result


def _service_node(path: str, text: str) -> dict[str, Any]:
    name = Path(path).stem
    publishes = sorted(set(_PUBLISH_RE.findall(text)) | set(_EMIT_RE.findall(text)))
    surfaces = sorted(set(_SURFACE_RE.findall(text)))
    imports_eventbus = "event_bus" in text or "core.eventbus" in text
    uses_llm = "daemon_llm_call" in text or "execute_public_safe_cheap_lane" in text
    uses_db = "core.runtime.db" in text or "connect()" in text
    reads_state = "load_json(" in text or "state_store" in text
    writes_state = "save_json(" in text or "state_store" in text
    return {
        "id": name,
        "path": path,
        "kind": _classify_service(name=name, text=text),
        "surface_count": len(surfaces),
        "surfaces": surfaces[:12],
        "publishes_count": len(publishes),
        "publishes": publishes[:16],
        "uses": {
            "eventbus": imports_eventbus,
            "llm": uses_llm,
            "db": uses_db,
            "state_store": reads_state or writes_state,
        },
        "coverage": {},
    }


def _daemon_nodes() -> list[dict[str, Any]]:
    try:
        from core.services import daemon_manager

        states = daemon_manager.get_all_daemon_states()
        registry = getattr(daemon_manager, "_REGISTRY", {})
    except Exception:
        return []
    result = []
    for item in states:
        name = str(item.get("name") or "")
        reg = registry.get(name, {}) if isinstance(registry, dict) else {}
        result.append({
            "id": name,
            "module": str(reg.get("module") or ""),
            "enabled": bool(item.get("enabled")),
            "cadence_minutes": item.get("effective_cadence_minutes"),
            "last_run_at": item.get("last_run_at") or "",
            "description": item.get("description") or "",
        })
    return result


def _surface_nodes(services: list[dict[str, Any]]) -> list[dict[str, Any]]:
    nodes: list[dict[str, Any]] = []
    for service in services:
        for surface in service.get("surfaces") or []:
            nodes.append({
                "id": f"{service['id']}::{surface}",
                "service": service["id"],
                "name": surface,
            })
    return nodes


def _event_family_nodes(services: list[dict[str, Any]]) -> list[dict[str, Any]]:
    families: dict[str, int] = {}
    for service in services:
        for kind in service.get("publishes") or []:
            family = str(kind).split(".", 1)[0]
            families[family] = families.get(family, 0) + 1
    return [
        {"id": family, "publish_markers": count}
        for family, count in sorted(families.items())
    ]


def _edges(
    *,
    services: list[dict[str, Any]],
    daemons: list[dict[str, Any]],
    surfaces: list[dict[str, Any]],
    event_families: list[dict[str, Any]],
    causal: dict[str, Any],
) -> list[dict[str, str]]:
    edges: list[dict[str, str]] = []
    service_ids = {str(s["id"]) for s in services}
    for daemon in daemons:
        module = str(daemon.get("module") or "")
        service = module.rsplit(".", 1)[-1]
        if service in service_ids:
            edges.append({"from": f"daemon:{daemon['id']}", "to": f"service:{service}", "type": "runs"})
    for surface in surfaces:
        edges.append({"from": f"service:{surface['service']}", "to": f"surface:{surface['name']}", "type": "exposes"})
    families = {str(item["id"]) for item in event_families}
    for service in services:
        for kind in service.get("publishes") or []:
            family = str(kind).split(".", 1)[0]
            if family in families:
                edges.append({"from": f"service:{service['id']}", "to": f"event:{family}", "type": "publishes"})
    for item in causal.get("family_edges") or []:
        parent = str(item.get("parent_family") or "")
        child = str(item.get("child_family") or "")
        if parent and child:
            edges.append({"from": f"event:{parent}", "to": f"event:{child}", "type": "observed-causes"})
    return edges[:1200]


def _causal_runtime_evidence(limit: int = 40) -> dict[str, Any]:
    try:
        from core.runtime.db import connect

        with connect() as conn:
            event_count = int(conn.execute("SELECT COUNT(*) FROM events").fetchone()[0])
            edge_count = int(conn.execute("SELECT COUNT(*) FROM causal_edges").fetchone()[0])
            rows = conn.execute(
                """
                SELECT
                    substr(parent.kind, 1, instr(parent.kind || '.', '.') - 1) AS parent_family,
                    substr(child.kind, 1, instr(child.kind || '.', '.') - 1) AS child_family,
                    parent.kind AS parent_kind,
                    child.kind AS child_kind,
                    ce.edge_kind AS edge_kind,
                    ce.source AS source,
                    COUNT(*) AS count,
                    AVG(ce.confidence) AS avg_confidence,
                    MAX(ce.created_at) AS last_seen_at
                FROM causal_edges ce
                JOIN events child ON child.id = ce.child_event_id
                JOIN events parent ON parent.id = ce.parent_event_id
                GROUP BY parent_family, child_family, parent.kind, child.kind, ce.edge_kind, ce.source
                ORDER BY count DESC, last_seen_at DESC
                LIMIT ?
                """,
                (max(1, int(limit)),),
            ).fetchall()
    except Exception as exc:
        return {
            "mode": "causal-runtime-unavailable",
            "event_count": 0,
            "edge_count": 0,
            "family_edges": [],
            "error": f"{type(exc).__name__}: {exc}"[:300],
        }

    family_edges = [
        {
            "parent_family": str(row["parent_family"] or ""),
            "child_family": str(row["child_family"] or ""),
            "parent_kind": str(row["parent_kind"] or ""),
            "child_kind": str(row["child_kind"] or ""),
            "edge_kind": str(row["edge_kind"] or ""),
            "source": str(row["source"] or ""),
            "count": int(row["count"] or 0),
            "avg_confidence": round(float(row["avg_confidence"] or 0.0), 3),
            "last_seen_at": str(row["last_seen_at"] or ""),
        }
        for row in rows
    ]
    return {
        "mode": "causal-runtime-v1",
        "event_count": event_count,
        "edge_count": edge_count,
        "family_edges": family_edges,
    }


def _dark_edges(services: list[dict[str, Any]]) -> list[dict[str, Any]]:
    dark: list[dict[str, Any]] = []
    for service in services:
        uses = service.get("uses") or {}
        if (uses.get("db") or uses.get("state_store") or service.get("publishes_count")) and not service.get("surface_count"):
            dark.append({
                "service": service["id"],
                "path": service["path"],
                "reason": "runtime/state/event influence with no local build_*surface marker",
                "kind": service["kind"],
            })
    return dark


def _rank_dark_edges(
    dark_edges: list[dict[str, Any]],
    *,
    causal: dict[str, Any],
    daemons: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    daemon_modules = {
        str(item.get("module") or "").rsplit(".", 1)[-1]
        for item in daemons
    }
    causal_families = {
        str(item.get("parent_family") or "")
        for item in causal.get("family_edges") or []
    } | {
        str(item.get("child_family") or "")
        for item in causal.get("family_edges") or []
    }
    ranked = []
    for edge in dark_edges:
        service = str(edge.get("service") or "")
        score, reasons = _dark_edge_score(
            service=service,
            kind=str(edge.get("kind") or ""),
            is_daemon=service in daemon_modules,
            has_causal_family=service.split("_", 1)[0] in causal_families,
        )
        item = dict(edge)
        item["priority_score"] = score
        item["priority"] = _priority_label(score)
        item["priority_reasons"] = reasons
        ranked.append(item)
    ranked.sort(
        key=lambda item: (
            -int(item.get("priority_score") or 0),
            str(item.get("service") or ""),
        )
    )
    return ranked[:80]


def _coverage_summary(services: list[dict[str, Any]]) -> dict[str, Any]:
    scored = []
    for service in services:
        score, parts = _coverage_score(service)
        item = {
            "service": service["id"],
            "path": service["path"],
            "kind": service["kind"],
            "score": score,
            "parts": parts,
        }
        service["coverage"] = item
        scored.append(item)
    scored.sort(key=lambda item: (int(item["score"]), str(item["service"])))
    low = [item for item in scored if int(item["score"]) < 45]
    avg = round(sum(int(item["score"]) for item in scored) / max(len(scored), 1), 1)
    return {
        "avg_score": avg,
        "low_count": len(low),
        "lowest": scored[:20],
    }


def _is_pure_utility(service: dict[str, Any]) -> bool:
    """Detect services that are pure helpers — no observable state, no IO,
    just synchronous functions. These shouldn't pull down coverage average.

    A service is a utility if it has ALL of:
      - No state imports (db, state_store)
      - No eventbus imports
      - No LLM calls
      - Not classified as daemon/action/signal
      - File is small (< 200 LOC heuristic, captured below)
    """
    uses = service.get("uses") or {}
    if uses.get("db") or uses.get("state_store"):
        return False
    if uses.get("eventbus"):
        return False
    if uses.get("llm"):
        return False
    if service.get("kind") in {"daemon", "action", "signal"}:
        return False
    # Pure utilities also rarely publish events
    if int(service.get("publishes_count") or 0) > 0:
        return False
    return True


def _coverage_score(service: dict[str, Any]) -> tuple[int, dict[str, int]]:
    # Pure utilities (config readers, formatters, constants) are exempt from
    # the coverage score — they don't have state to surface, so dragging
    # them through the same observability rubric is meaningless. Marked at
    # full score 100 so they don't pull down the average. (2026-05-13)
    if _is_pure_utility(service):
        return 100, {"exempt": "pure-utility"}

    uses = service.get("uses") or {}
    kind = service.get("kind")

    # Kind-aware bonus (2026-05-13): "surface" and "signal" modules are
    # read-only aggregators by design — their job is to project state for
    # observation, not to emit new events. Don't penalise them for the
    # absent "events" axis. They get a 20pt observer-role bonus to mirror
    # what daemon/action gets for being a mutator-role.
    observer_role = 20 if kind in {"surface", "signal"} else 0

    parts = {
        "surface": 25 if int(service.get("surface_count") or 0) > 0 else 0,
        "events": 20 if int(service.get("publishes_count") or 0) > 0 else 0,
        "eventbus": 15 if uses.get("eventbus") else 0,
        "state": 15 if (uses.get("db") or uses.get("state_store")) else 0,
        "llm": 10 if uses.get("llm") else 0,
        "daemon_or_action": 15 if kind in {"daemon", "action"} else 0,
        "observer_role": observer_role,
    }
    return min(sum(parts.values()), 100), parts


def _system_health_from_jarvis_perspective(
    *,
    dark_edges: list[dict[str, Any]],
    coverage: dict[str, Any],
    theater: dict[str, Any],
    recommended: dict[str, Any] | None,
) -> dict[str, Any]:
    top_dark = dark_edges[:5]
    lowest = list(coverage.get("lowest") or [])[:5]
    theater_summary = theater.get("summary") if isinstance(theater, dict) else {}
    theater_high = int((theater_summary or {}).get("high_risk") or 0)
    return {
        "mode": "jarvis-perspective-system-health",
        "state": "needs-witness" if top_dark or theater_high else "well-witnessed",
        "summary": (
            f"{len(dark_edges)} dark influence edges; "
            f"{coverage.get('low_count', 0)} low-coverage services; "
            f"{theater_high} high-risk theater prompts; "
            f"next: {recommended.get('title') if recommended else 'none'}"
        ),
        "least_visible_influential": top_dark,
        "lowest_coverage": lowest,
        "theater_high_risk": theater.get("files", [])[:5] if isinstance(theater, dict) else [],
        "recommended_theater_refactor": (
            theater.get("recommendedTheaterTask") if isinstance(theater, dict) else None
        ),
        "recommended_next": recommended,
    }


def _dark_edge_score(
    *,
    service: str,
    kind: str,
    is_daemon: bool,
    has_causal_family: bool,
) -> tuple[int, list[str]]:
    score = 40
    reasons = ["runtime influence without local MC surface marker"]
    if is_daemon:
        score += 30
        reasons.append("registered daemon")
    if has_causal_family:
        score += 20
        reasons.append("family appears in observed causal graph")
    if kind in {"action", "memory", "signal"}:
        score += 12
        reasons.append(f"{kind} layer")
    if any(token in service for token in ("approval", "repair", "executive", "tool", "memory", "identity", "governance")):
        score += 18
        reasons.append("touches protected agency/continuity surface")
    return min(score, 140), reasons


def _priority_label(score: int) -> str:
    if score >= 105:
        return "high"
    if score >= 75:
        return "medium"
    return "low"


def _observability_task_from_dark_edge(edge: dict[str, Any]) -> dict[str, Any]:
    service = str(edge.get("service") or "")
    return {
        "id": f"observability-{service}",
        "title": f"Expose {service} in Mission Control",
        "goal": (
            "Add or connect a minimal build_*surface / MC projection for "
            f"{service}, then rerun System Cartographer to verify the dark edge clears."
        ),
        "scope": str(edge.get("path") or service),
        "task_kind": "observability_bridge_repair",
        "priority": str(edge.get("priority") or "medium"),
        "priority_score": int(edge.get("priority_score") or 0),
        "reason": "; ".join(edge.get("priority_reasons") or []),
        "source": "system-cartographer",
    }


def _maybe_enqueue_observability_task(candidate: dict[str, Any] | None) -> dict[str, Any]:
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
    duplicate = _find_existing_observability_task(candidate)
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
        return {
            "enabled": True,
            "status": "enqueued",
            "task_id": str(task.get("task_id") or ""),
            "priority_score": score,
        }
    except Exception as exc:
        logger.debug("system_cartographer: auto task enqueue failed: %s", exc)
        return {
            "enabled": True,
            "status": "enqueue-failed",
            "error": f"{type(exc).__name__}: {exc}"[:300],
            "priority_score": score,
        }


def _find_existing_observability_task(candidate: dict[str, Any]) -> dict[str, Any] | None:
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


def _maybe_enqueue_theater_task(candidate: dict[str, Any] | None) -> dict[str, Any]:
    if not candidate:
        return {"enabled": True, "status": "no-candidate"}
    score = int(candidate.get("priority_score") or 0)
    if score < _THEATER_AUTO_TASK_MIN_SCORE:
        return {
            "enabled": True,
            "status": "below-threshold",
            "threshold": _THEATER_AUTO_TASK_MIN_SCORE,
            "priority_score": score,
        }
    duplicate = _find_existing_theater_task(candidate)
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
            kind=_THEATER_AUTO_TASK_KIND,
            goal=str(candidate.get("goal") or candidate.get("title") or ""),
            scope=str(candidate.get("scope") or ""),
            origin=_THEATER_AUTO_TASK_ORIGIN,
            priority=_runtime_task_priority(str(candidate.get("priority") or "")),
            owner="jarvis",
        )
        return {
            "enabled": True,
            "status": "enqueued",
            "task_id": str(task.get("task_id") or ""),
            "priority_score": score,
        }
    except Exception as exc:
        logger.debug("system_cartographer: theater task enqueue failed: %s", exc)
        return {
            "enabled": True,
            "status": "enqueue-failed",
            "error": f"{type(exc).__name__}: {exc}"[:300],
            "priority_score": score,
        }


def _find_existing_theater_task(candidate: dict[str, Any]) -> dict[str, Any] | None:
    try:
        from core.services.runtime_tasks import list_tasks

        scope = str(candidate.get("scope") or "").strip()
        goal = str(candidate.get("goal") or "").strip()
        for status in ("queued", "running", "blocked"):
            for task in list_tasks(status=status, kind=_THEATER_AUTO_TASK_KIND, limit=50):
                task_scope = str(task.get("scope") or "").strip()
                if scope and task_scope == scope:
                    return task
                if not scope and str(task.get("goal") or "").strip() == goal:
                    return task
    except Exception:
        return None
    return None


def _runtime_task_priority(priority: str) -> str:
    normalized = str(priority or "").strip().lower()
    if normalized in {"high", "medium", "low"}:
        return normalized
    return "medium"


def _theater_audit_surface() -> dict[str, Any]:
    try:
        from core.services.theater_audit import build_theater_audit_surface

        return build_theater_audit_surface()
    except Exception as exc:
        return {
            "mode": "theater-audit-unavailable",
            "summary": {"findings": 0, "high_risk": 0, "medium_risk": 0, "low_risk": 0},
            "error": f"{type(exc).__name__}: {exc}"[:300],
        }


def _tool_count() -> int:
    path = _REPO_ROOT / "core" / "tools" / "simple_tools.py"
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return 0
    return len(set(_TOOL_RE.findall(text)))


def _classify_service(*, name: str, text: str) -> str:
    lowered = f"{name}\n{text[:1000]}".lower()
    if "daemon" in lowered:
        return "daemon"
    if "signal" in lowered or "tracking" in lowered:
        return "signal"
    if "memory" in lowered or "brain" in lowered:
        return "memory"
    if "executive" in lowered or "action" in lowered or "tool" in lowered:
        return "action"
    if "surface" in lowered or "mission control" in lowered:
        return "surface"
    return "service"
