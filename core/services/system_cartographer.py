"""System Cartographer — broad map of Jarvis' runtime and inner layers.

This is wider than the Agency Map vision edges. It inventories code/runtime
surfaces so Jarvis can ask "what exists in me, what emits, what is visible, and
what is probably still dark?"
"""
from __future__ import annotations

import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parents[2]

_PUBLISH_RE = re.compile(r"event_bus\.publish\(\s*[\"']([^\"']+)[\"']")
_EMIT_RE = re.compile(r"emit\(\s*[\"']([^\"']+)[\"']")
_SURFACE_RE = re.compile(r"def\s+(build_[a-zA-Z0-9_]*surface)\s*\(")
_TOOL_RE = re.compile(r"[\"']name[\"']\s*:\s*[\"']([^\"']+)[\"']")


def build_system_cartographer_surface() -> dict[str, Any]:
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
    dark_edges = _rank_dark_edges(_dark_edges(services), causal=causal, daemons=daemons)
    recommended_observability_task = (
        _observability_task_from_dark_edge(dark_edges[0]) if dark_edges else None
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
        "notes": [
            "Phase 1 is code/runtime inventory, not proof of causal influence.",
            "Phase 2 adds eventbus/causal_edges runtime evidence.",
            "Next phase should persist deltas over time and rank missing witness surfaces.",
        ],
    }


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
